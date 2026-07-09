#!/usr/bin/env python3
"""
Walmart 爬虫专用的飞书最小客户端。

从 about-sif 的 sif_feishu_sync.py 裁剪而来——只保留 walmart_report / walmart_bot
用到的能力（建表、建工作表、读写区域、扩行列、矩阵覆写），去掉所有 Sif 业务逻辑，
让 walmart-scraper 子目录完全自包含、不依赖 about-sif 任何模块。

对外提供：
  - FeishuClient：飞书表格客户端（tenant_access_token 管理 + 表格/工作表/区域操作）
  - overwrite_sheet_with_matrix(client, spreadsheet_token, sheet_id, matrix)
      把二维矩阵覆写到工作表（自动扩行列、分块写），返回 (rows, cols)
"""

import time
from urllib.parse import quote

import requests


# ============================================================================
# 飞书开放平台 API
# ============================================================================

FEISHU_TENANT_TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
)
FEISHU_SHEET_META_URL = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{token}"
FEISHU_SHEETS_QUERY_URL = (
    "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{token}/sheets/query"
)
FEISHU_VALUES_URL = (
    "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values/{range}"
)
FEISHU_VALUES_UPDATE_URL = (
    "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values"
)
FEISHU_DIMENSION_RANGE_URL = (
    "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/dimension_range"
)
FEISHU_CREATE_SPREADSHEET_URL = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets"
FEISHU_BATCH_UPDATE_SHEETS_URL = (
    "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/sheets_batch_update"
)


def request_json(method, url, *, retries=5, retry_delay=1.5, timeout=30, **kwargs):
    """带重试的 HTTP 请求，返回 JSON。"""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == retries:
                break
            sleep_seconds = retry_delay * attempt
            print(f"请求失败，{sleep_seconds:.1f}s 后重试 ({attempt}/{retries})：{exc}")
            time.sleep(sleep_seconds)

    raise RuntimeError(f"请求失败，已重试 {retries} 次: {last_error}") from last_error


# ============================================================================
# 飞书表格客户端
# ============================================================================

class FeishuClient:
    """飞书表格最小客户端（仅覆盖 walmart 所需能力）。"""

    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token = None

    def _request(self, method, url, **kwargs):
        payload = request_json(method, url, timeout=30, **kwargs)
        if payload.get("code") not in (0, None):
            raise RuntimeError(
                f"飞书接口失败: code={payload.get('code')} msg={payload.get('msg')}"
            )
        return payload

    def get_tenant_access_token(self):
        if self._tenant_access_token:
            return self._tenant_access_token

        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        data = self._request("POST", FEISHU_TENANT_TOKEN_URL, json=payload)
        self._tenant_access_token = data["tenant_access_token"]
        return self._tenant_access_token

    def _headers(self):
        return {"Authorization": f"Bearer {self.get_tenant_access_token()}"}

    def get_spreadsheet_token(self, token_like):
        """把 wiki token 解析成 spreadsheet_token；本身已是 spreadsheet_token 则原样返回。"""
        try:
            data = self._request(
                "GET",
                FEISHU_SHEET_META_URL.format(token=token_like),
                headers=self._headers(),
            )
            return data["data"]["spreadsheet"]["token"]
        except Exception:
            return token_like

    def read_range(self, spreadsheet_token, sheet_id, range_str):
        encoded_range = quote(f"{sheet_id}!{range_str}", safe="!:$")
        url = FEISHU_VALUES_URL.format(token=spreadsheet_token, range=encoded_range)
        data = self._request(
            "GET",
            url,
            headers=self._headers(),
            params={"valueRenderOption": "UnformattedValue"},
        )
        return data.get("data", {}).get("valueRange", {}).get("values", [])

    def write_range(self, spreadsheet_token, sheet_id, range_str, values):
        raw_range = f"{sheet_id}!{range_str}"
        url = FEISHU_VALUES_UPDATE_URL.format(token=spreadsheet_token)
        payload = {"valueRange": {"range": raw_range, "values": values}}
        self._request(
            "PUT",
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
        )

    def list_sheets(self, spreadsheet_token):
        data = self._request(
            "GET",
            FEISHU_SHEETS_QUERY_URL.format(token=spreadsheet_token),
            headers=self._headers(),
        )
        return data.get("data", {}).get("sheets", [])

    def get_sheet_info(self, spreadsheet_token, sheet_id):
        for sheet in self.list_sheets(spreadsheet_token):
            if sheet.get("sheet_id") == sheet_id:
                return sheet
        raise RuntimeError(f"找不到工作表: {sheet_id}")

    def add_dimension(self, spreadsheet_token, sheet_id, major_dimension, length):
        if length <= 0:
            return

        payload = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": major_dimension,
                "length": length,
            }
        }
        self._request(
            "POST",
            FEISHU_DIMENSION_RANGE_URL.format(token=spreadsheet_token),
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
        )

    def create_spreadsheet(self, title, folder_token=None):
        """新建电子表格。folder_token 为 None 时建在应用根目录。

        返回 {"spreadsheet_token", "url", "title"}。
        """
        body = {"title": title}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._request(
            "POST",
            FEISHU_CREATE_SPREADSHEET_URL,
            headers={**self._headers(), "Content-Type": "application/json"},
            json=body,
        )
        spreadsheet = data["data"]["spreadsheet"]
        return {
            "spreadsheet_token": spreadsheet["spreadsheet_token"],
            "url": spreadsheet.get("url", ""),
            "title": spreadsheet.get("title", title),
        }

    def create_sheet(self, spreadsheet_token, title, index=0):
        """在电子表格中新建工作表，index 默认 0（插在最前）。

        返回 {"sheet_id", "title", "index"}。
        """
        body = {
            "requests": [
                {"addSheet": {"properties": {"title": title, "index": index}}}
            ]
        }
        data = self._request(
            "POST",
            FEISHU_BATCH_UPDATE_SHEETS_URL.format(token=spreadsheet_token),
            headers={**self._headers(), "Content-Type": "application/json"},
            json=body,
        )
        props = data["data"]["replies"][0]["addSheet"]["properties"]
        return {
            "sheet_id": props["sheetId"],
            "title": props.get("title", title),
            "index": props.get("index", index),
        }


# ============================================================================
# 矩阵覆写（自动扩行列 + 分块写入）
# ============================================================================

def col_index_to_name(index):
    """0 -> A, 25 -> Z, 26 -> AA"""
    result = []
    while True:
        index, remainder = divmod(index, 26)
        result.append(chr(65 + remainder))
        if index == 0:
            break
        index -= 1
    return "".join(reversed(result))


def pad_matrix(values, min_rows, min_cols):
    padded = [list(row) + [""] * (max(min_cols, len(row)) - len(row)) for row in values]
    width = max([min_cols, *(len(row) for row in padded)] if padded else [min_cols])

    for row in padded:
        if len(row) < width:
            row.extend([""] * (width - len(row)))

    while len(padded) < min_rows:
        padded.append([""] * width)

    return padded


def build_probe_range(matrix, row_buffer=20, col_buffer=6):
    rows = max(len(matrix) + row_buffer, 100)
    cols = max(max((len(row) for row in matrix), default=0) + col_buffer, 26)
    last_col = col_index_to_name(cols - 1)
    return f"A1:{last_col}{rows}"


def overwrite_sheet_with_matrix(client, spreadsheet_token, sheet_id, matrix):
    """把二维矩阵覆写到工作表，自动扩行列、分块写入。返回 (rows, cols)。"""
    sheet_info = client.get_sheet_info(spreadsheet_token, sheet_id)
    grid = sheet_info.get("grid_properties", {})
    current_rows = int(grid.get("row_count", 0))
    current_cols = int(grid.get("column_count", 0))

    probe_range = build_probe_range(matrix)

    try:
        existing_values = client.read_range(spreadsheet_token, sheet_id, probe_range)
    except RuntimeError as exc:
        if "90221" in str(exc):
            existing_values = []
        else:
            raise

    old_rows = len(existing_values)
    old_cols = max((len(row) for row in existing_values), default=0)
    new_rows = len(matrix)
    new_cols = max((len(row) for row in matrix), default=0)

    rows = max(old_rows, new_rows)
    cols = max(old_cols, new_cols)

    client.add_dimension(spreadsheet_token, sheet_id, "ROWS", rows - current_rows)
    client.add_dimension(spreadsheet_token, sheet_id, "COLUMNS", cols - current_cols)

    final_matrix = pad_matrix(matrix, rows, cols)

    row_chunk_size = 200
    col_chunk_size = 30

    for start_col in range(0, cols, col_chunk_size):
        end_col = min(start_col + col_chunk_size, cols)
        col_start_name = col_index_to_name(start_col)
        col_end_name = col_index_to_name(end_col - 1)

        for start_row in range(0, rows, row_chunk_size):
            chunk = [
                row[start_col:end_col]
                for row in final_matrix[start_row : start_row + row_chunk_size]
            ]
            row_start = start_row + 1
            row_end = start_row + len(chunk)
            range_str = f"{col_start_name}{row_start}:{col_end_name}{row_end}"
            client.write_range(spreadsheet_token, sheet_id, range_str, chunk)

    return rows, cols
