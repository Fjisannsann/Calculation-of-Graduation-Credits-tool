const pdfjsLib = await import("https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/build/pdf.min.mjs");

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/build/pdf.worker.min.mjs";

const statusEl = document.getElementById("status");
const runButton = document.getElementById("run-button");
const fileInput = document.getElementById("pdf-input");
const csvDownloadsEl = document.getElementById("csv-downloads");
const resultTableBody = document.querySelector("#result-table tbody");
const summaryEl = document.getElementById("summary");

const REPLACE_DICT = {
  "Academic Engli sh": "Academic English",
  "Practi calEngli sh": "Practical English",
  "Academi c Engl i sh": "Academic English",
  "Pr act i cal Engl i sh": "Practical English",
  "I II": "III",
};

const ROMAN_CHAR_MAP = {
  "Ⅰ": "I",
  "Ⅱ": "II",
  "Ⅲ": "III",
  "Ⅳ": "IV",
  "Ⅴ": "V",
  "Ⅵ": "VI",
  "Ⅶ": "VII",
  "Ⅷ": "VIII",
  "Ⅸ": "IX",
  "Ⅹ": "X",
};

function normalizeText(text) {
  let value = (text ?? "").normalize("NFKC");

  value = value.replace(/\r?\n/g, " ").replace(/\t/g, " ");
  value = value.replace(/(\d)\.\s+(\d)/g, "$1.$2");
  value = value.replace(/\bI\s+I\s+I\b/g, "III");
  value = value.replace(/\bI\s+I\b/g, "II");
  value = value.replace(/\bV\s+I\b/g, "VI");
  value = value.replace(/\bI\s+V\b/g, "IV");

  Object.entries(REPLACE_DICT).forEach(([from, to]) => {
    value = value.replaceAll(from, to);
  });

  value = value.replace(/([A-Za-z一-龥ぁ-んァ-ンー])([IVX]+)\b/g, "$1 $2");
  value = value.replace(/\s+/g, " ").trim();

  Object.entries(ROMAN_CHAR_MAP).forEach(([roman, ascii]) => {
    value = value.replaceAll(roman, ascii);
  });
  return value;
}

function normalizeSubjectName(text) {
  return normalizeText(text).replace(/\s+/g, "");
}

function subjectKey(text) {
  return normalizeSubjectName(text).toLowerCase();
}

function toFloat(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) ? number : 0;
}

function toInt(value) {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) ? number : 0;
}

function stripBracket(text, open, close) {
  return normalizeText(text).replace(open, "").replace(close, "");
}

function toLinesByY(items) {
  const groups = new Map();

  for (const item of items) {
    if (!item.str || !item.str.trim()) continue;
    const x = item.transform[4];
    const y = Math.round(item.transform[5] * 2) / 2;
    if (!groups.has(y)) groups.set(y, []);
    groups.get(y).push({ x, str: item.str });
  }

  return [...groups.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([, row]) =>
      row
        .sort((a, b) => a.x - b.x)
        .map((item) => item.str)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim(),
    )
    .filter(Boolean);
}

function toLinesByEol(items) {
  const lines = [];
  let buffer = [];
  for (const item of items) {
    if (item.str && item.str.trim()) buffer.push(item.str);
    if (item.hasEOL) {
      const line = buffer.join(" ").replace(/\s+/g, " ").trim();
      if (line) lines.push(line);
      buffer = [];
    }
  }
  if (buffer.length) {
    const line = buffer.join(" ").replace(/\s+/g, " ").trim();
    if (line) lines.push(line);
  }
  return lines;
}

async function extractPdfLines(file) {
  const data = new Uint8Array(await file.arrayBuffer());
  const pdf = await pdfjsLib.getDocument({ data }).promise;
  const allLines = [];

  for (let pageIndex = 1; pageIndex <= pdf.numPages; pageIndex += 1) {
    const page = await pdf.getPage(pageIndex);
    const textContent = await page.getTextContent();
    const items = textContent.items ?? [];
    const hasEol = items.some((item) => item.hasEOL);
    const lines = hasEol ? toLinesByEol(items) : toLinesByY(items);
    allLines.push(...lines);
  }
  return allLines;
}

function parseRowsFromLines(lines, subjectMetaMap) {
  let categoryBig = "";
  let categoryMid = "";
  let categorySmall = "";
  const rows = [];

  for (const rawLine of lines) {
    const line = normalizeText(rawLine);
    if (!line) continue;

    if (/^【.+】$/.test(line)) {
      categoryBig = stripBracket(line, "【", "】");
      categoryMid = "";
      categorySmall = "";
      continue;
    }
    if (/^[<＜].+[>＞]$/.test(line)) {
      categoryMid = line.replace(/[<＜>＞]/g, "").trim();
      categorySmall = "";
      continue;
    }
    if (/^[（(].+[）)]$/.test(line)) {
      categorySmall = line.replace(/^[（(]/, "").replace(/[）)]$/, "").trim();
      continue;
    }
    if (
      line.includes("小計") ||
      line.includes("総計") ||
      line.includes("科目計") ||
      line.includes("成績通知書") ||
      line.includes("GPA")
    ) {
      continue;
    }

    const matched = line.match(/^(\d+(?:\.\d+)?)\s+([0-5])\s+(\d{2})(.+)$/);
    if (!matched) continue;

    const credits = matched[1];
    const grade = matched[2];
    const year = matched[3];
    const subjectParsed = normalizeSubjectName(matched[4]);
    const subjectData = subjectMetaMap.get(subjectKey(subjectParsed));

    rows.push({
      category_big: subjectData?.category_big ?? categoryBig,
      category_mid: subjectData?.category_mid ?? categoryMid,
      category_small: subjectData?.category_small ?? categorySmall,
      category_detail: subjectData?.category_detail ?? "",
      subject: subjectData?.subject ?? subjectParsed,
      credits,
      grade,
      year,
    });
  }

  return rows;
}

function toCsv(rows) {
  const header = [
    "category_big",
    "category_mid",
    "category_small",
    "category_detail",
    "subject",
    "credits",
    "grade",
    "year",
  ];
  const escaped = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const lines = [header.join(",")];

  for (const row of rows) {
    lines.push(header.map((key) => escaped(row[key])).join(","));
  }
  return lines.join("\n");
}

function createCreditBucket() {
  return {
    big: new Map(),
    mid: new Map(),
    small: new Map(),
    detail: new Map(),
    subject: new Map(),
    all: 0,
  };
}

function addMapCredit(map, key, value) {
  if (!key) return;
  map.set(key, (map.get(key) ?? 0) + value);
}

function resolveRowAttribute(row, typeName) {
  if (typeName === "all" || typeName === "group") return "";
  if (typeName === "category_subject") return row.subject;
  return row[typeName] ?? "";
}

function calculateCredits(rows, typeMap, subjectFlags) {
  const credits = createCreditBucket();
  const creditsByFlag = new Map();

  for (const row of rows) {
    const grade = toInt(row.grade);
    if (grade <= 1) continue;

    const credit = toFloat(row.credits);
    credits.all += credit;

    typeMap.forEach((typeName, typeKey) => {
      if (typeKey === "all" || typeKey === "group") return;
      const key = resolveRowAttribute(row, typeName);
      if (!key) return;
      addMapCredit(credits[typeKey], key, credit);
    });

    const flag = subjectFlags.get(subjectKey(row.subject));
    if (flag === undefined) continue;

    if (!creditsByFlag.has(flag)) creditsByFlag.set(flag, createCreditBucket());
    const flagged = creditsByFlag.get(flag);
    flagged.all += credit;
    typeMap.forEach((typeName, typeKey) => {
      if (typeKey === "all" || typeKey === "group") return;
      const key = resolveRowAttribute(row, typeName);
      if (!key) return;
      addMapCredit(flagged[typeKey], key, credit);
    });
  }

  return { credits, creditsByFlag };
}

function calculateGroupTotals(requirementGroups, credits) {
  const totals = new Map();

  for (const group of requirementGroups) {
    const id = group.id;
    const type = group.type;
    const name = group.name;
    const current = totals.get(id) ?? 0;

    if (type === "all") totals.set(id, current + credits.all);
    if (type === "big") totals.set(id, current + (credits.big.get(name) ?? 0));
    if (type === "mid") totals.set(id, current + (credits.mid.get(name) ?? 0));
    if (type === "small") totals.set(id, current + (credits.small.get(name) ?? 0));
    if (type === "detail") totals.set(id, current + (credits.detail.get(name) ?? 0));
    if (type === "subject") totals.set(id, current + (credits.subject.get(name) ?? 0));
  }
  return totals;
}

function checkRequirements(graduationCredits, credits, creditsByFlag, groupTotals) {
  const results = [];

  for (const requirement of graduationCredits) {
    const required = toFloat(requirement.required_credits);
    const type = requirement.type;
    const name = requirement.name;
    const flagRaw = requirement.flag;
    const flag = flagRaw === "" ? null : toInt(flagRaw);

    let current = 0;
    if (type === "group") current = groupTotals.get(requirement.id) ?? 0;
    else if (type === "all") current = credits.all;
    else if (flag !== null) current = creditsByFlag.get(flag)?.[type]?.get(name) ?? 0;
    else current = credits[type]?.get(name) ?? 0;

    const shortage = required - current;
    results.push({
      id: requirement.id,
      label: flag === null ? name : `${name} (flag=${flag})`,
      current,
      required,
      shortage,
      isOk: shortage <= 0,
    });
  }
  return results;
}

function renderResults(results) {
  resultTableBody.innerHTML = "";

  for (const result of results) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${result.label}</td>
      <td>${result.current.toFixed(1)}</td>
      <td>${result.required.toFixed(1)}</td>
      <td>${result.shortage > 0 ? result.shortage.toFixed(1) : "0.0"}</td>
      <td class="${result.isOk ? "ok" : "ng"}">${result.isOk ? "OK" : "不足"}</td>
    `;
    resultTableBody.appendChild(tr);
  }

  const allOk = results.length > 0 && results.every((result) => result.isOk);
  summaryEl.innerHTML = `<p class="${allOk ? "ok" : "ng"}">${
    allOk ? "総合判定: 卒業要件を満たしています" : "総合判定: 卒業要件を満たしていません"
  }</p>`;
}

function renderCsvDownloads(files) {
  csvDownloadsEl.innerHTML = "";
  files.forEach((item) => {
    const a = document.createElement("a");
    a.href = item.url;
    a.download = item.filename;
    a.textContent = `${item.filename} をダウンロード`;
    csvDownloadsEl.appendChild(a);
  });
}

async function loadDatabases() {
  const paths = {
    type: "./data/type.json",
    subjectFlags: "./data/subject_flags.json",
    subjects: "./data/subjects.json",
    requirementGroups: "./data/requirement_groups.json",
    graduationCredits: "./data/graduation_credits.json",
  };

  const [type, subjectFlags, subjects, requirementGroups, graduationCredits] = await Promise.all(
    Object.values(paths).map((path) => fetch(path).then((response) => response.json())),
  );

  const typeMap = new Map(type.map((row) => [row.type, row.type_name]));
  const subjectFlagsMap = new Map(subjectFlags.map((row) => [subjectKey(row.subject), toInt(row.flag)]));
  const subjectMetaMap = new Map(subjects.map((row) => [subjectKey(row.subject), row]));

  return {
    typeMap,
    subjectFlagsMap,
    subjectMetaMap,
    requirementGroups,
    graduationCredits,
  };
}

const dbPromise = loadDatabases();

runButton.addEventListener("click", async () => {
  const files = [...(fileInput.files ?? [])];
  if (files.length === 0) {
    statusEl.textContent = "PDFを1つ以上選択してください。";
    return;
  }

  runButton.disabled = true;
  summaryEl.textContent = "";
  resultTableBody.innerHTML = "";
  statusEl.textContent = "処理中です...";

  const objectUrls = [];

  try {
    const db = await dbPromise;
    const mergedRows = [];
    const csvFiles = [];

    for (const file of files) {
      const lines = await extractPdfLines(file);
      const rows = parseRowsFromLines(lines, db.subjectMetaMap);
      mergedRows.push(...rows);

      const csvText = toCsv(rows);
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      objectUrls.push(url);
      csvFiles.push({
        url,
        filename: `${file.name.replace(/\.pdf$/i, "")}.csv`,
      });
    }

    renderCsvDownloads(csvFiles);

    const { credits, creditsByFlag } = calculateCredits(
      mergedRows,
      db.typeMap,
      db.subjectFlagsMap,
    );
    const groupTotals = calculateGroupTotals(db.requirementGroups, credits);
    const results = checkRequirements(db.graduationCredits, credits, creditsByFlag, groupTotals);
    renderResults(results);

    statusEl.textContent = `完了: ${files.length}件のPDFから ${mergedRows.length} 科目を抽出しました。`;
  } catch (error) {
    console.error(error);
    statusEl.textContent = "処理に失敗しました。PDF形式を確認してください。";
  } finally {
    runButton.disabled = false;
    window.setTimeout(() => {
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    }, 60_000);
  }
});
