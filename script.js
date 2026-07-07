// 工作时间配置
const WORK_START = 9 * 60;          // 9:00
const LUNCH_START = 12 * 60 + 30;   // 12:30
const LUNCH_END = 14 * 60;          // 14:00
const WORK_END = 18 * 60 + 30;      // 18:30

// 总工作时长（分钟）
const TOTAL_WORK_MINUTES = (LUNCH_START - WORK_START) + (WORK_END - LUNCH_END);

// 鼓励语（解构、克制、诗意 —— 贴合 Margiela 气质）
const MOTTOS = {
    beforeWork: ['A NEW DAY, UNWRITTEN.', 'BEGIN WITH QUIET CERTAINTY.', 'THE STUDIO AWAITS.'],
    morning: ['STEADY HANDS. CLEAR MIND.', 'FORM FOLLOWS FOCUS.', 'EVERY MINUTE, A STITCH.'],
    lunch: ['PAUSE. BREATHE. EAT.', 'SILENCE IS A MATERIAL.', 'REST IS PART OF THE WORK.'],
    afternoon: ['THE FINAL MARGIN APPROACHES.', 'HOLD THE LINE.', 'ALMOST UNSTITCHED FROM THE DAY.'],
    afterWork: ['FREE AT LAST.', 'THE DAY IS YOURS TO KEEP.', 'OFF DUTY. UNDEFINED.']
};

// Margiela 编号系列（0-23 体系中的子集）
const SERIES = [
    { no: '4',  name: '— ACCESSORIES' },
    { no: '6',  name: '— MM6' },
    { no: '10', name: '— SHOES' },
    { no: '11', name: '— INTERLUDE' },
    { no: '22', name: '— TIMEPIECE' },
];
let seriesIndex = SERIES.findIndex(s => s.no === '22'); // 默认 22 TIMEPIECE

function applySeries() {
    const s = SERIES[seriesIndex];
    document.getElementById('seriesNum').textContent = s.no;
    document.getElementById('seriesName').textContent = s.name;
    document.body.setAttribute('data-series', s.no);
}

function nextSeries() {
    seriesIndex = (seriesIndex + 1) % SERIES.length;
    const selector = document.getElementById('seriesSelector');
    selector.classList.add('switching');
    setTimeout(() => {
        applySeries();
        localStorage.setItem('mm-series', SERIES[seriesIndex].no);
    }, 160);
    setTimeout(() => selector.classList.remove('switching'), 420);
}

// 恢复上次选择的系列
const savedSeries = localStorage.getItem('mm-series');
if (savedSeries) {
    const idx = SERIES.findIndex(s => s.no === savedSeries);
    if (idx >= 0) seriesIndex = idx;
}
applySeries();
document.getElementById('seriesSelector').addEventListener('click', nextSeries);

function getCurrentMinutes() {
    const now = new Date();
    return now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;
}

function pad(num) {
    return String(Math.floor(num)).padStart(2, '0');
}

function update() {
    const now = new Date();
    const currentMin = getCurrentMinutes();

    const hoursEl = document.getElementById('hours');
    const minutesEl = document.getElementById('minutes');
    const secondsEl = document.getElementById('seconds');
    const titleEl = document.getElementById('title');
    const statusText = document.getElementById('statusText');
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressLabel = document.getElementById('progressLabel');
    const currentTimeEl = document.getElementById('currentTime');
    const currentDateEl = document.getElementById('currentDate');
    const mottoEl = document.getElementById('motto');

    // 当前时间 / 日期
    currentTimeEl.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    currentDateEl.textContent = `${pad(now.getDate())} ${months[now.getMonth()]}`;

    // 清除 active
    document.querySelectorAll('.schedule-item').forEach(el => el.classList.remove('active'));

    let targetMinutes, status, titleText, mottoKey, progress, scheduleIndex;

    if (currentMin < WORK_START) {
        targetMinutes = WORK_START;
        status = 'PRE · SHIFT';
        titleText = 'UNTIL ONSET';
        mottoKey = 'beforeWork';
        progress = 0;
        progressLabel.textContent = 'PENDING';
        scheduleIndex = 0;
    } else if (currentMin < LUNCH_START) {
        targetMinutes = LUNCH_START;
        status = 'IN · SESSION';
        titleText = 'UNTIL INTERLUDE';
        mottoKey = 'morning';
        progress = ((currentMin - WORK_START) / TOTAL_WORK_MINUTES) * 100;
        progressLabel.textContent = 'PROGRESS';
        scheduleIndex = 0;
    } else if (currentMin < LUNCH_END) {
        targetMinutes = LUNCH_END;
        status = 'INTERLUDE';
        titleText = 'UNTIL RESUME';
        mottoKey = 'lunch';
        progress = ((LUNCH_START - WORK_START) / TOTAL_WORK_MINUTES) * 100;
        progressLabel.textContent = 'PAUSED';
        scheduleIndex = 1;
    } else if (currentMin < WORK_END) {
        targetMinutes = WORK_END;
        status = 'IN · SESSION';
        titleText = 'UNTIL DEPARTURE';
        mottoKey = 'afternoon';
        progress = (((LUNCH_START - WORK_START) + (currentMin - LUNCH_END)) / TOTAL_WORK_MINUTES) * 100;
        progressLabel.textContent = 'PROGRESS';
        scheduleIndex = 2;
    } else {
        targetMinutes = null;
        status = 'OFF · DUTY';
        titleText = 'SHIFT COMPLETE';
        mottoKey = 'afterWork';
        progress = 100;
        progressLabel.textContent = 'COMPLETE';
        scheduleIndex = 2;
        document.body.classList.add('celebrate');
    }

    // 高亮当前日程
    const items = document.querySelectorAll('.schedule-item');
    if (items[scheduleIndex]) items[scheduleIndex].classList.add('active');

    // 倒计时数字
    if (targetMinutes !== null) {
        const diffSec = (targetMinutes - currentMin) * 60;
        hoursEl.textContent = pad(diffSec / 3600);
        minutesEl.textContent = pad((diffSec % 3600) / 60);
        secondsEl.textContent = pad(diffSec % 60);
    } else {
        hoursEl.textContent = '00';
        minutesEl.textContent = '00';
        secondsEl.textContent = '00';
    }

    statusText.textContent = status;
    titleEl.textContent = titleText;

    const mottos = MOTTOS[mottoKey];
    mottoEl.textContent = mottos[now.getMinutes() % mottos.length];

    progress = Math.min(100, Math.max(0, progress));
    progressFill.style.width = progress + '%';
    progressPercent.textContent = progress.toFixed(1) + '%';
}

update();
setInterval(update, 1000);
