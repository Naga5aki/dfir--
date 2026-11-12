# 一题一进程的手机取证编排器（v2：动态预算 / 有界重试 / 无进展停止）
# 设计目标：更快得到有证据支持的正确答案；未完成题保留可恢复的 pending，不无限重试。
#
# 用法：
#   powershell -File dfir-solve.ps1 -Questions 11-20
#   powershell -File dfir-solve.ps1 -Questions 11,12 -MaxTurns 8 -Budget 480
#   powershell -File dfir-solve.ps1 -Questions 1-8 -DryRun
#
# 预算层级：
#   基础题：MaxTurns/Budget（默认 12/480）
#   复杂题：ComplexQuestions（默认 15,16,19）用 ComplexTurns/ComplexBudget（16/600）
#   首次失败且仍有具体下一步：只再用 RetryTurns/RetryBudget（默认 6/240），不重新拿完整预算
#   撞硬墙 / 工具阻塞 / 已列出已排除路径：不再重试
# MYOS：批量前 myos_compact.py 生成 device_map.myos.*；MCP 失败自动回退 raw/证据包
# 案件级：notes\complex-questions.txt 控制 16/600，notes\deep-questions.txt 控制是否用 dfir-max
# 多题集：按请求题号范围唯一匹配 questions-*.txt
# 每题判定：pending-<题号>.md 的答案行不是 UNKNOWN/未取到/待确认 -> OK。

param(
    [Parameter(Mandatory = $true)][string]$Questions,
    [string]$HermesCommand = 'hermes',
    [int]$MaxTurns = 12,
    [int]$Budget = 480,
    [int]$RetryTurns = 6,
    [int]$RetryBudget = 240,
    [int]$ComplexTurns = 16,
    [int]$ComplexBudget = 600,
    [string]$ComplexQuestions = '15,16,19',
    [string]$DeepQuestions = '',
    [int]$BatchBudgetSeconds = 0,
    [string]$CaseRoot = '',
    [string]$QuestionsFile = '',
    # 计算机题：-Domain computer 强制使用计算机 prompt/技能；留空则按题面自动判断。
    [string]$Domain = '',
    [string]$Skills = '',
    [switch]$Resume,
    [switch]$KeepMounted,
    [switch]$SkipMount,
    [switch]$AllowMissingQuestion,
    [switch]$SkipEvidencePack,
    [switch]$SkipMyos,
    [switch]$SkipEvalGold,
    [string]$SolveCaseId = '',
    [string]$SolveMaterialId = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'
$python = 'C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe'
# Python 3.14 has the local mcp client used by myos_compact.py.
$pythonMyos = 'C:\Users\TWK\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$bin = 'D:\ForensicsAgent\hermes\bin'
# Allow tests/alternate installs to pin the CLI; default keeps PATH lookup.
$hermesInvoke = if ($HermesCommand -match '\s') { '"' + $HermesCommand + '"' } else { $HermesCommand }

function Resolve-CaseRoot([string]$explicit) {
    # An explicit root is authoritative: a typo must fail, not silently fall back
    # to D:\forensics\cases and write into the wrong case notes.
    if ($explicit) {
        if (Test-Path -LiteralPath $explicit) {
            return (Resolve-Path -LiteralPath $explicit).Path
        }
        return $null
    }
    $candidates = @('D:\forensics\cases')
    $candidates += @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.Root 'Forensics\cases' })
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) {
            return (Resolve-Path -LiteralPath $c).Path
        }
    }
    return $null
}

function Get-ComplexList {
    return @($ComplexQuestions -split ',' |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^\d+$' } |
        ForEach-Object { [int]$_ })
}

function Get-DeepList {
    # Deep profile gets the extra reverse-engineering MCPs. If no explicit
    # deep list is supplied, preserve the old behavior (complex == deep).
    $raw = if ($DeepQuestions) { $DeepQuestions } else { $ComplexQuestions }
    return @($raw -split ',' |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^\d+$' } |
        ForEach-Object { [int]$_ })
}

function Get-Profile([int]$q) {
    if ((Get-DeepList) -contains $q) { return 'dfir-max' }
    return 'dfir-myos'
}

function Expand-Questions([string]$spec) {
    $out = @()
    foreach ($part in ($spec -split ',')) {
        $p = $part.Trim()
        if ($p -match '^(\d+)-(\d+)$') {
            $out += ($Matches[1]..$Matches[2])
        } elseif ($p -match '^\d+$') {
            $out += [int]$p
        }
    }
    return $out
}

function Get-Sig([string]$path) {
    if (-not (Test-Path $path)) { return 'absent' }
    $i = Get-Item $path
    return "$($i.LastWriteTime.Ticks)-$($i.Length)"
}

# 未完成题的最低可恢复收口：只在模型没有留下任何 pending 时写，绝不覆盖已有证据。
function Write-FallbackPending([int]$q, [string]$verdict, [string]$pending, [string]$logPath) {
    if (Test-Path $pending) {
        $existing = Get-Content $pending -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($existing -and $existing.Trim()) { return }
    }
    $next = switch ($verdict) {
        'TOOL_BLOCKED'      { '核对当前 case/mount 与 sqlite_query dbPath；修复 not authorized/BLOCKED 后，用同一题面单独重跑' }
        'BUDGET_EXHAUSTED'  { '读取本轮日志的最后有效工具输出；缩小到一个具体查询后单独重跑' }
        'TIMEOUT'           { '检查日志最后进度；把下一项操作拆成单个低成本查询后单独重跑' }
        'NO_QUESTION'       { '补齐 notes\questions-*.txt 的第 ' + $q + ' 题题面后重跑' }
        default             { '检查本轮日志最后错误；按具体线索单独重跑' }
    }
    $logName = if ($logPath) { Split-Path $logPath -Leaf } else { '' }
    $body = @(
        "题$q（自动收口：$verdict）"
        "答案：UNKNOWN"
        "证据：未取得可核验原始字段；最后日志：$logName"
        "已排除：$verdict（自动判定）"
        "下一轮：$next"
    )
    Set-Content -Path $pending -Value $body -Encoding UTF8
}

# 题面必须逐字进 prompt；找不到就报 NO_QUESTION，绝不拿空题面或旧题面硬跑
function Get-QuestionText([int]$q) {
    if (-not (Test-Path $QuestionsFile)) { return '' }
    $lines = @(Get-Content $QuestionsFile -Encoding UTF8)
    foreach ($line in $lines) {
        if ($line -match ('^{0}\|(.*)$' -f $q)) { return $Matches[1].Trim() }
    }
    # 兼容"每行一题、无编号"的题面文件
    if ($q -ge 1 -and $q -le $lines.Count) {
        $line = $lines[$q - 1].Trim()
        if ($line -and $line -notmatch '\|') { return $line }
    }
    return ''
}

function Get-DomainFromText([string]$text, [int]$q) {
    if ($Domain) { return $Domain }
    # 先用检材号/镜像类型锁定计算机题；手机题即使提到“电脑密码”也保持 mobile。
    if ($text -match '检材三|电脑检材|计算机取证|\bE01\b|磁盘镜像|openKylin|Linux镜像|Windows镜像') { return 'computer' }
    if ($text -match '手机|检材二|android|安卓|\bapk\b|imei|\buin\b') { return 'mobile' }
    if ($text -match '电脑|计算机|注册表|NTUSER|Prefetch|EVTX') { return 'computer' }
    if ($text -match '微信|便签|备忘录|联系人|短信|相册') { return 'mobile' }
    return 'generic'
}

function Get-Route([string]$text) {
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("route-" + [guid]::NewGuid().ToString('N') + ".txt")
    Set-Content -LiteralPath $tmp -Value $text -Encoding UTF8
    try {
        $json = & $python -X utf8 "$bin\dfir_router.py" --route-file $tmp
        if ($LASTEXITCODE -ne 0 -or -not $json) { return $null }
        return ($json | ConvertFrom-Json)
    } finally {
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
    }
}

function Get-SkillsForDomain([string]$d, [string]$text) {
    if ($Skills) { return $Skills }
    $routed = Get-Route $text
    $base = switch ($d) {
        'mobile' { 'android-app-forensics,mobile-ctf-pipeline' }
        'computer' {
            if ($text -match 'Windows|windows|注册表|NTUSER|Prefetch|EVTX|BitLocker|vhd|VHD') {
                'myos-results-analysis,windows-loader,digital-forensics'
            } else {
                'myos-results-analysis,linux-loader,digital-forensics'
            }
        }
        default { 'myos-results-analysis' }
    }
    if ($routed -and $routed.skill -and $base -notlike "$($routed.skill)*") {
        return "$($routed.skill),$base"
    }
    return $base
}

function Get-EffectiveBudget([int]$q, [string]$packFile) {
    $turns = if ((Get-ComplexList) -contains $q) { $ComplexTurns } else { $MaxTurns }
    $sec = if ((Get-ComplexList) -contains $q) { $ComplexBudget } else { $Budget }
    # 有预取证据包且较大时，给少量额外轮次/时间；不是无条件放大
    if ($packFile -and (Test-Path $packFile) -and ((Get-Item $packFile).Length -gt 2200)) {
        $turns += 2
        $sec += 60
    }
    return [pscustomobject]@{ Turns = [int]$turns; Budget = [int]$sec; Complex = ((Get-ComplexList) -contains $q) }
}

function New-Prompt([int]$q, [string]$profile, [string]$text, [string]$prev, [string]$pack,
                    [switch]$Retry, [int]$Turns, [int]$BudgetSec, [string]$CaseNotes,
                    [string]$Domain, [string]$SkillsArg, $Route = $null) {
    $retryLine = if ($Retry) { "这是重试：只带上一步的具体线索，不要重复上一轮工具迭代的路径枚举；若上一轮指向体检为 0 行/缺库的源，直接跳过并换分支。" } else { "" }
    $prevBlock = if ($prev) { @"
上一轮遗留内容（文件已归档；只能当线索，必须自行复核后重新取数，禁止原样照抄）：
$prev
"@ } else { "" }
    $packBlock = if ($pack -and (Test-Path $pack)) { @"
证据包（脚本已按题型预取候选值与取数入口，先读这一份，**不要重新枚举包/库/列**）：
$pack
"@ } else { "" }
    $writeBy = [int][math]::Max(2, [math]::Ceiling($Turns / 3.0))
    $firstJump = ''
    if ($Route -and $Route.command) {
        $firstJump = @"
第一跳（本轮第一个取证工具调用必须是下面这条；在此之前只允许读本题索引文件 $($Route.index_file)，不要 skill_view，不要 ls 全盘）：
$($Route.command)
禁止：$($Route.forbid)

"@
    }

    if ($Domain -eq 'computer') {
        $computerIndex = Join-Path $CaseNotes 'device_map.computer.summary.txt'
        $computerBlock = if (Test-Path -LiteralPath $computerIndex) { @"
计算机取证索引（先读这一份，不要重读 70KB 概览）：
$computerIndex
"@ } else { @"
尚未生成计算机取证索引：先调用 query_computer_forensics_results_overview(caseId) 一次，把结果落盘到 $CaseNotes\overview.computer.json；用 sqliteQueryHints/integrateForensicsDatabases 取插件库路径，不要分段反复读整份 JSON。
"@ }
        return @"
题面（第 $q 题）：$text

只回答这一题，不要回答其他题。

$firstJump
$packBlock

$computerBlock

硬性步骤（按序，最多 $Turns 次工具调用迭代 / $BudgetSec 秒；--max-turns 指工具调用次数，预算由外层传入）：
0. 先读 $CaseNotes\device_map.computer.summary.txt（若有）：按「题型速查」选插件库，不要从 45 个库里逐个试。需要关键词定位时，先跑 `python D:\ForensicsAgent\hermes\bin\computer_keyword_search.py --question "<题面>" --notes $CaseNotes --root <Root> --execute --timeout 60 --max-hits 30`，看命中文件/表再打开。
1. 插件库优先：所有 `.mfs` 用 MCP `sqlite_query`；先 `SELECT name, sql FROM sqlite_master WHERE type='table'` 一次，再一条有界 SELECT。不要用 python sqlite3 打开 `.mfs`。
   开关机 → Linux_SystemInfo.TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN；USB → Linux_UsbInfo；微信 → Win_WeChat.mfs；浏览器密码 → Any_Chrome/Any_ChromiumBrowser（v11 用 chrome_login_decrypt.py）；文档元数据 → Any_OfficeMetaInfo；文件哈希 → FSData.mfs（md5 可能为空，候选现算）.
2. 插件库没有的正文/图片/嵌套 VM：先 `query_device_mount_path(materialId)` 拿 `/c/osmap/.../Root/PartitionN`；先看数据盘 home/<user>、文档/桌面/下载；不要对 13GB 文档树全量 grep。
   命中 `我的测试机/`、`虚拟机/`、`.vmware/`、`*.vmdk` 时按嵌套 VM 处理：先跑 `python D:\ForensicsAgent\hermes\bin\myos_nested_vm.py --case-id <id> --vmdk <vmdk> --dry-run`，确认后 `--yes`（内部 add_image_material→load_case→query_device_mount_path）；不要提交重新取证任务；在 VM 内找便签/浏览器/微信。
3. 文件伪装：docx 可能是 ZIP（PK 文件头）→ 解出 XML → 看 FFD8FFE0/JFIF 改 .jpg；先复制副本，原件只读。音频先转写；长音频异常分段取每段首字连读。
4. 题面选项与四源证据冲突时，最多再交叉验证一次；按选项一致值或问用户一次，不要用 20 轮证明出题人错。
5. 写文件要前置：第 $writeBy 轮结束前先写 $CaseNotes\pending-$q.md（先 UNKNOWN），之后取到关键字段就覆盖更新；覆盖前先 read_file 再 write_file。
   格式：
   题$q（一句话题意）
   答案：<严格符合题面【答案格式】的最终值>
   证据：<root 相对路径 + 表名 + 关键字段值>
   已排除：<走过的错误分支，没有写 无>
   下一轮：<若仍不确定，写下一步；已确定写 完成>
6. 答案行只允许一个最终值；不确定写 答案：UNKNOWN，不要编造，不要把题面示例值当答案。
7. 无论成功失败，必须写 pending-$q.md 再结束；不写文件等于本题未作答。

预算纪律：出现新证据/缩小候选/排除具体假设/修复工具错误才继续；连续 2 次工具迭代没有新增证据或同一工具/查询连续 2 次失败且没有新修复路径 -> 立即收口写 pending。
隔离规则：notes 目录内只允许读 $CaseNotes\device_map.computer.*、$CaseNotes\overview.computer.json、本题的 $CaseNotes\evidence-q$q.txt 和本题待写的 $CaseNotes\pending-$q.md；检材原始数据只读访问不受限。
禁止读 notes 下其它 pending、_solve-*.log、cases\archive，以及任何 gold/eval/参考答案。

$retryLine

$prevBlock
当前 profile=$profile；已加载技能=$SkillsArg；证据只读，禁止写入检材目录。
"@
    }

    $myosBlock = if (Test-Path -LiteralPath (Join-Path $CaseNotes 'device_map.myos.summary.txt')) { @"
MYOS 已完成分析结果（优先使用，不要从零重复解析）：
先读 $CaseNotes\device_map.myos.summary.txt；其中的 appMfsPath 指向 MYOS 已解析的 App/微信库，用 sqlite_query 精确查询；sqliteQueryHints 给出 MApps.mfs 的查询入口。MYOS 未解析的 notes/realm/图片 OCR 再走原始目录或证据包。
"@ } else { "" }
    return @"
题面（第 $q 题）：$text

只回答这一题，不要回答其他题。

$firstJump
$packBlock

$myosBlock

硬性步骤（按序，最多 $Turns 次工具调用迭代 / $BudgetSec 秒；--max-turns 指工具调用次数，预算由外层传入）：
0. 先读 MYOS 索引（若有）和上面的证据包：候选值列表必须逐个复核（找到原始记录行才算数，禁止照抄）；候选为空时按「取数入口」定向打开，不要回到包清单从头逛。
1. 再读 $CaseNotes\device_map.summary.txt：顶部「数据源体检」里 0 行/缺库的源直接跳过，不要再花轮次试；「线索速查」按题型给出直查入口，优先照它取数。需要细节再读 device_map.json（packages 是 list，按包名遍历，不要用 .get()）。
2. 按已加载的 android-app-forensics / mobile-ctf-pipeline 技能中的"题型→直查路径"取数；聊天类题目优先看 summary 里"含聊天库的包"。
3. 取数**一律**用现成脚本，不要写多行 python -c（Windows 引号嵌套必错）：
   python D:\ForensicsAgent\hermes\bin\dbq.py "<root>\data\data\<包名>\databases\<库>.db" --tables
   python D:\ForensicsAgent\hermes\bin\dbq.py "<root>\...\<库>.db" "SELECT <列> FROM <表> WHERE <条件>"
   dbq.py 自动展开 <root>、强制只读、首行列名；加 --json 出结构化。
   已解析 App 的 `.mfs` 用 MCP `sqlite_query` 查 MYOS 索引里的 appMfsPath，不要用 python sqlite3 打开 `.mfs`；明文库才用 dbq.py。
   包名、库名、表名、列名一律取自 device_map / MYOS 索引或刚才 --tables 的输出，**不要套用示例里的名字**。
   取数优先用 terminal；execute_code 可能因审批或引号问题失败，失败一次就改用 terminal，不要连续重试。
4. 写文件要**前置**：第 $writeBy 轮结束前先写一次 $CaseNotes\pending-$q.md（答案先写 UNKNOWN 占位），
   之后每取到一个关键字段就用整文件覆盖更新；**不要**把写盘留到最后几轮。
   **覆盖前必须先 read_file 读一遍 pending-$q.md 再 write_file**，否则工具会以"未见过该文件当前内容"为由拒绝覆盖。
   格式：
   题$q（一句话题意）
   答案：<严格符合题面【答案格式】的最终值>
   证据：<root 相对路径 + 表名 + 关键字段值>
   已排除：<走过的错误分支，没有写 无>
   下一轮：<若仍不确定，写下一步；已确定写 完成>
5. 答案行只允许一个最终值；不确定时写 答案：UNKNOWN，不要编造，也不要把题面示例值当答案。
   写 UNKNOWN 时「证据：」行必须给出**关键线索**（已定位到的库/表/文件 + 已看到的候选值 + 还差哪一步），
   「下一轮：」必须写出一条具体可执行的命令。
6. 无论成功失败，**必须**写 pending-$q.md 再结束；不写文件等于本题未作答。

预算纪律（可观察信号，不要靠模型自评）：
- 出现新相关证据、缩小候选、排除具体假设、或修复工具错误 -> 可以继续。
- 连续 2 次工具迭代没有新增证据/没有缩小候选，或同一工具/查询连续 2 次失败且没有新修复路径 -> 立即收口，写 pending 后停止。
- sqlite_query 的 dbPath 必须来自当前案件的 mount/overview/sqliteQueryHints/device_map；遇到 not authorized 先 query_open_cases -> query_materials -> query_*_overview 核对 caseId 和 mount root，**不要原样重试同一路径**；明文库用 dbq.py。
- 剩余预算不足以完成下一项高成本操作时，不要启动；先落盘。
- 不要无限"继续想一想"；没有新证据就停止。

隔离规则：notes 目录内只允许读 $CaseNotes\device_map.*、$CaseNotes\tool-map.md、本题的 $CaseNotes\evidence-q$q.txt 和本题待写的 $CaseNotes\pending-$q.md；检材原始数据的只读访问不受此限。
禁止读 notes 下其它文件、_solve-*.log、pending-*.md、cases\archive，以及任何 gold/eval/参考答案文件；
本题答案只能来自检材原始数据或 device_map 指向的库，不得引用历史记录里的结论。

$retryLine

$prevBlock
当前 profile=$profile；已加载技能=$SkillsArg；证据只读，禁止写入检材目录。
"@
}

$qs = Expand-Questions $Questions
if ($qs.Count -eq 0) { Write-Error "Questions 参数无法解析：$Questions"; exit 2 }

$caseRoot = Resolve-CaseRoot $CaseRoot
if (-not $caseRoot) {
    Write-Error "找不到取证案例目录（D:\forensics\cases 或各盘 Forensics\cases）；请检查外置盘/挂载后重试。"
    exit 2
}
$notes = Join-Path $caseRoot 'notes'
if (-not (Test-Path -LiteralPath $notes)) { New-Item -ItemType Directory -Force -Path $notes | Out-Null }
$solveLog = Join-Path $notes '_solve.log'

# Per-case strategy sidecars. Explicit CLI values win; files let a case keep
# its own complex/deep classification without editing the script.
if (-not $PSBoundParameters.ContainsKey('ComplexQuestions')) {
    $cf = Join-Path $notes 'complex-questions.txt'
    if (Test-Path -LiteralPath $cf) {
        $v = (Get-Content -LiteralPath $cf -Raw -Encoding UTF8).Trim()
        if ($v) { $ComplexQuestions = $v; Write-Host "使用案件复杂题清单：$ComplexQuestions" }
    }
}
if (-not $PSBoundParameters.ContainsKey('DeepQuestions')) {
    $df = Join-Path $notes 'deep-questions.txt'
    if (Test-Path -LiteralPath $df) {
        $v = (Get-Content -LiteralPath $df -Raw -Encoding UTF8).Trim()
        if ($v) { $DeepQuestions = $v; Write-Host "使用案件深度题清单：$DeepQuestions" }
    }
}

if (-not $QuestionsFile) {
    $cands = @(Get-ChildItem -LiteralPath $notes -Filter 'questions-*.txt' -File -ErrorAction SilentlyContinue)
    if ($cands.Count -eq 0) {
        Write-Error "notes 下没有 questions-*.txt；请用 -QuestionsFile 指定题面，避免空题面硬跑。"
        exit 2
    }
    if ($cands.Count -eq 1) {
        $QuestionsFile = $cands[0].FullName
        Write-Host "使用题面文件：$QuestionsFile（请确认与当前案件匹配）"
    } else {
        # Multiple题集: pick the single file whose filename range covers all
        # requested questions; otherwise keep the explicit-file requirement.
        $matching = @()
        foreach ($c in $cands) {
            $m = [regex]::Match($c.Name, '^questions-(\d+)-(\d+)\.txt$')
            if ($m.Success) {
                $lo = [int]$m.Groups[1].Value; $hi = [int]$m.Groups[2].Value
                $outside = @($qs | Where-Object { $_ -lt $lo -or $_ -gt $hi })
                if ($outside.Count -eq 0) { $matching += $c }
            }
        }
        if ($matching.Count -eq 1) {
            $QuestionsFile = $matching[0].FullName
            Write-Host "按题号范围选择题面文件：$QuestionsFile"
        } else {
            Write-Error ("notes 下有多个 questions-*.txt，且无法唯一匹配题号 $($qs -join ',')；请用 -QuestionsFile 明确指定。")
            exit 2
        }
    }
}
if (-not (Test-Path -LiteralPath $QuestionsFile)) {
    Write-Error "题面文件不存在：$QuestionsFile"
    exit 2
}

# 自动选中唯一题面文件时，文件名范围必须覆盖要做的题，避免拿旧题集静默跑出 NO_QUESTION。
if (-not $PSBoundParameters.ContainsKey('QuestionsFile') -and -not $AllowMissingQuestion -and
    (Split-Path $QuestionsFile -Leaf) -match '^questions-(\d+)-(\d+)\.txt$') {
    $qLo = [int]$Matches[1]; $qHi = [int]$Matches[2]
    $outside = @($qs | Where-Object { $_ -lt $qLo -or $_ -gt $qHi })
    if ($outside.Count -gt 0) {
        Write-Error ("自动选中的题面文件 $([IO.Path]::GetFileName($QuestionsFile)) 只覆盖 {0}-{1}，但请求包含 {2}；请用 -QuestionsFile 指定当前题集。" -f $qLo, $qHi, ($outside -join ','))
        exit 2
    }
}

# Per-question-file sidecars: questions-457-471.txt -> complex-questions-457-471.txt.
# This lets mobile and computer batches keep separate budgets without a global override.
$rangeTag = ''
if ((Split-Path $QuestionsFile -Leaf) -match '^questions-(\d+)-(\d+)\.txt$') {
    $rangeTag = "$($Matches[1])-$($Matches[2])"
}
if ($rangeTag) {
    if (-not $PSBoundParameters.ContainsKey('ComplexQuestions')) {
        $cfRange = Join-Path $notes "complex-questions-$rangeTag.txt"
        if (Test-Path -LiteralPath $cfRange) {
            $v = (Get-Content -LiteralPath $cfRange -Raw -Encoding UTF8).Trim()
            if ($v) { $ComplexQuestions = $v; Write-Host "使用题集复杂题清单：$cfRange -> $v" }
        }
    }
    if (-not $PSBoundParameters.ContainsKey('DeepQuestions')) {
        $dfRange = Join-Path $notes "deep-questions-$rangeTag.txt"
        if (Test-Path -LiteralPath $dfRange) {
            $v = (Get-Content -LiteralPath $dfRange -Raw -Encoding UTF8).Trim()
            if ($v) { $DeepQuestions = $v; Write-Host "使用题集深度题清单：$dfRange -> $v" }
        }
    }
}

Set-Location $caseRoot
$batchStart = Get-Date

try {
    if (-not $DryRun) {
        if (-not $SkipMount) {
            & $python "$bin\myos_mount.py" mount *> $null
            if ($LASTEXITCODE -ne 0) { Write-Warning "MYOS 挂载失败（exit $LASTEXITCODE）；将使用现有挂载继续。" }
            # 数据源地图：一次性索引，模型不再枚举包与库
            & $python "$bin\myos_appmap.py" *> $null
        }
        if (-not $SkipMyos) {
            if (Test-Path -LiteralPath $pythonMyos) {
                & $pythonMyos "$bin\myos_compact.py" --notes $notes --case-id $SolveCaseId --material-id $SolveMaterialId *> $null
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "MYOS 分析结果索引生成失败（exit $LASTEXITCODE）；继续用 device_map/证据包兜底。"
                } elseif (Test-Path -LiteralPath (Join-Path $notes 'device_map.myos.summary.txt')) {
                    Write-Host "已生成 MYOS 分析结果索引：device_map.myos.summary.txt"
                }
            } else {
                Write-Warning "找不到带 mcp 客户端的 Python（$pythonMyos）；跳过 MYOS 结果索引。"
            }
        }
        # 计算机题：一次性生成插件库索引，避免模型反复读 70KB 概览。
        $hasComputer = @($qs | Where-Object {
            (Get-DomainFromText (Get-QuestionText $_) $_) -eq 'computer'
        }).Count -gt 0
        if ($hasComputer -and -not $SkipMyos -and (Test-Path -LiteralPath $pythonMyos)) {
            & $pythonMyos "$bin\myos_computer_compact.py" --notes $notes --case-id $SolveCaseId *> $null
            if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $notes 'device_map.computer.summary.txt'))) {
                Write-Host "已生成计算机取证索引：device_map.computer.summary.txt"
            } else {
                Write-Warning "计算机取证索引生成失败；模型将自行查询概览。"
            }
        }
        if (-not (Test-Path (Join-Path $notes 'device_map.json'))) {
            Write-Warning "device_map.json 未生成，本轮退回逐题探索（会更慢）"
        }
    }

    foreach ($q in $qs) {
        $profile = Get-Profile $q
        $pending = Join-Path $notes "pending-$q.md"
        $attempt = 0
        $verdict = 'FAILED'
        $total = 0
        $attemptProfile = $profile

        # 整批预算：剩余不足以完成一次基础尝试时，记录断点并停止后续题
        if ($BatchBudgetSeconds -gt 0 -and -not $DryRun) {
            $remaining = $BatchBudgetSeconds - ((Get-Date) - $batchStart).TotalSeconds
            if ($remaining -lt [math]::Max(180, $Budget)) {
                $remainingQs = @($qs | Where-Object { $_ -ge $q })
                $stopFile = Join-Path $notes '_batch_budget_stop.md'
                $body = @(
                    "批量预算耗尽：BatchBudgetSeconds=$BatchBudgetSeconds，剩余题：$($remainingQs -join ',')",
                    "时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
                    "下一步：提高批量预算，或单独运行这些题；已完成题不受影响。"
                )
                Set-Content -Path $stopFile -Value $body -Encoding UTF8
                $line = "Q$q | $profile | 0s | SKIP_BATCH_BUDGET | attempt=0 | $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                Write-Host $line
                Add-Content -Path $solveLog -Value $line -Encoding UTF8
                break
            }
        }

        # 续跑：已有非 UNKNOWN 答案的不重跑
        if ($Resume -and (Test-Path $pending)) {
            $ans = (Select-String -Path $pending -Pattern '答案\s*[：:]' | Select-Object -Last 1).Line
            if ($ans -and $ans -notmatch 'UNKNOWN|未取到|待确认') {
                $skip = "Q{0} | {1} | 0s | SKIP(已有答案) | attempt=0 | {2}" -f $q, $profile, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
                Write-Host $skip
                if (-not $DryRun) { Add-Content -Path $solveLog -Value $skip -Encoding UTF8 }
                continue
            }
        }

        $qText = Get-QuestionText $q
        $qDomain = Get-DomainFromText $qText $q
        $qRoute = Get-Route $qText
        $skillsArg = Get-SkillsForDomain $qDomain $qText
        if (-not $qText -and -not $AllowMissingQuestion) {
            $line = "Q$q | $profile | 0s | NO_QUESTION | attempt=0 | $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            Write-Host $line
            if (-not $DryRun) {
                Write-FallbackPending $q 'NO_QUESTION' $pending ''
                Add-Content -Path $solveLog -Value $line -Encoding UTF8
            }
            continue
        }

        # 证据包只服务手机题；计算机题改用 device_map.computer.summary.txt
        $packFile = Join-Path $notes "evidence-q$q.txt"
        if (-not $DryRun -and -not $SkipEvidencePack -and $qText -and $qDomain -eq 'mobile') {
            & $python "$bin\evidence_pack.py" --q $q --text $qText --out $packFile *> $null
        } elseif ($DryRun -or -not $qText -or $qDomain -ne 'mobile') {
            $packFile = ''
        }
        $eff = Get-EffectiveBudget $q $packFile

        if ($DryRun) {
            $qState = if ($qText) { 'QUESTION_OK' } else { 'NO_QUESTION' }
            $packState = if ($packFile -and (Test-Path $packFile)) { "$((Get-Item $packFile).Length)B" } else { 'none' }
            $first = if ($qRoute -and $qRoute.command) { $qRoute.command } else { 'none' }
            Write-Host ("Q{0} | {1} | domain={2} | skills={3} | turns={4} budget={5}s | complex={6} | {7} | pack={8} | first={9}" -f `
                $q, $profile, $qDomain, $skillsArg, $eff.Turns, $eff.Budget, $eff.Complex, $qState, $packState, $first)
            continue
        }

        # 上一轮留了 UNKNOWN：先归档，内容作为线索注入首轮 prompt
        $prevHint = ''
        if (Test-Path $pending) {
            $oldAns = (Select-String -Path $pending -Pattern '答案\s*[：:]' | Select-Object -Last 1).Line
            if ($oldAns -and $oldAns -match 'UNKNOWN|未取到|待确认') {
                $prevHint = Get-Content $pending -Raw -Encoding UTF8
                $prevDir = 'D:\ForensicsAgent\hermes\state\eval_runs\prev'
                New-Item -ItemType Directory -Force -Path $prevDir | Out-Null
                Move-Item $pending (Join-Path $prevDir ("pending-$q.unresolved.md")) -Force
            }
        }

        $attemptTurns = $eff.Turns
        $attemptBudget = $eff.Budget

        # 只有普通失败才重试；撞墙/工具阻塞/证据耗尽都是终态
        while ($attempt -lt 2 -and $verdict -notin @('OK', 'EXHAUSTED', 'TIMEOUT', 'TOOL_BLOCKED', 'BUDGET_EXHAUSTED', 'NO_QUESTION')) {
            $attempt++
            $before = Get-Sig $pending
            $prevText = $prevHint
            if ($attempt -gt 1 -and (Test-Path $pending)) {
                $prevText = (Get-Content $pending -Raw -Encoding UTF8)
                $prevDir = 'D:\ForensicsAgent\hermes\state\eval_runs\prev'
                New-Item -ItemType Directory -Force -Path $prevDir | Out-Null
                Move-Item $pending (Join-Path $prevDir ("pending-$q.a{0}.md" -f ($attempt - 1))) -Force
            }
            $prompt = New-Prompt $q $attemptProfile $qText $prevText $packFile -Retry:($attempt -gt 1) -Turns $attemptTurns -BudgetSec $attemptBudget -CaseNotes $notes -Domain $qDomain -SkillsArg $skillsArg -Route $qRoute
            $promptFile = Join-Path $notes "_solve-q$q.prompt.txt"
            Set-Content -Path $promptFile -Value $prompt -Encoding UTF8
            $sw = [Diagnostics.Stopwatch]::StartNew()

            # 硬墙钟：--run-budget 只在两轮之间检查，单轮长生成会穿透预算
            $log = "$notes\_solve-q$q-a$attempt.log"
            $inner = $hermesInvoke + ' -p ' + $attemptProfile + ' chat --query-file "' + $promptFile + '" --oneshot -Q --yolo' +
                ' --max-turns ' + $attemptTurns + ' --run-budget ' + $attemptBudget +
                ' -s ' + $skillsArg + ' --in "' + $caseRoot + '" > "' + $log + '" 2>&1'
            Set-Content -Path (Join-Path $notes "_solve-q$q-a$attempt.cmdline.txt") -Value $inner -Encoding UTF8
            $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $inner -PassThru -WindowStyle Hidden
            $hardLimit = $attemptBudget + 60
            $hitWall = $false
            try {
                Wait-Process -Id $proc.Id -Timeout $hardLimit -ErrorAction Stop
            } catch {
                & taskkill /PID $proc.Id /T /F *> $null
                $hitWall = $true
                "Q$q 达到硬墙钟 $hardLimit s，已终止（日志见 _solve-q$q-a$attempt.log）" | Write-Warning
            }

            $sw.Stop()
            $total += [int]$sw.Elapsed.TotalSeconds

            $after = Get-Sig $pending
            $answerLine = if (Test-Path $pending) {
                (Select-String -Path $pending -Pattern '答案\s*[：:]' | Select-Object -Last 1).Line
            } else { '' }

            if ($after -ne $before -and $answerLine -and $answerLine -notmatch 'UNKNOWN|未取到|待确认') {
                $verdict = 'OK'
            } elseif ($after -ne $before -and $answerLine -match 'UNKNOWN|未取到|待确认') {
                # 有证据支撑的 UNKNOWN 是合规收口，不是失败；不要触发重试覆盖它。
                $verdict = 'UNKNOWN'
            } else {
                $logText = Get-Content "$notes\_solve-q$q-a$attempt.log" -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
                $esc = [char]27
                $clean = ($logText -replace ([regex]::Escape($esc) + '\[[0-9;]*m'), '') -replace '│', ''
                $matches2 = [regex]::Matches($clean, '(?m)^[\s+>*-]*答案\s*[：:]\s*([^\r\n]+)')
                if ($matches2.Count -gt 0) {
                    $rescued = $matches2[$matches2.Count - 1].Groups[1].Value.Trim()
                    if ($rescued -and $rescued -notmatch 'UNKNOWN|未取到|待确认|<|>') {
                        $body = @(
                            "题$q（由 stdout 抢救写入，原始记录见 _solve-q$q-a$attempt.log）"
                            "答案：$rescued"
                            "证据：见 _solve-q$q-a$attempt.log 的核实过程"
                            "已排除：见日志"
                            "下一轮：完成"
                        )
                        Set-Content -Path $pending -Value $body -Encoding UTF8
                        $verdict = 'OK'
                    }
                }
                $pendingText = if (Test-Path $pending) { Get-Content $pending -Raw -Encoding UTF8 } else { '' }
                $hasNext = $pendingText -match '(?m)^\s*下一轮\s*[：:]\s*(?!完成\s*$|无\s*$)\S'
                $hasExcluded = $false
                if (Test-Path $pending) {
                    $exclLine = (Select-String -Path $pending -Pattern '已排除\s*[：:]' | Select-Object -Last 1).Line
                    if ($exclLine -and $exclLine -notmatch '已排除\s*[：:]\s*无\s*$') { $hasExcluded = $true }
                }
                $toolBlocked = $logText -match '(?i)(?:tool|mcp|sqlite_query|terminal|read_file|write_file)[^\r\n]{0,140}(?:not authorized|not a known tool name|permission denied|拒绝访问|blocked|does not exist|no such file)'
                $hitIteration = $logText -match '(?i)ran out of steps|max_iterations|maximum number of iterations'

                if ($verdict -ne 'OK') {
                    if ($hitWall) {
                        $verdict = 'TIMEOUT'
                    } elseif ($toolBlocked) {
                        $verdict = 'TOOL_BLOCKED'
                    } elseif ($hasExcluded -and -not $hasNext) {
                        $verdict = 'EXHAUSTED'
                    } elseif ($hitIteration -and -not $hasNext) {
                        $verdict = 'BUDGET_EXHAUSTED'
                    } elseif ($attempt -eq 1) {
                        # 有具体下一步（或普通失败）：只给缩短预算，不重新拿完整预算
                        $attemptTurns = [int][math]::Max(4, [math]::Min($RetryTurns, $eff.Turns))
                        $attemptBudget = [int][math]::Max(180, [math]::Min($RetryBudget, $eff.Budget))
                        $needsMax = $eff.Complex -or ($logText + $pendingText) -match '(?i)jadx|wiremcp|ida|pcap|apk|加密|reverse'
                        if ($needsMax) { $attemptProfile = 'dfir-max' }
                    }
                }
            }
        }

        if ($verdict -ne 'OK') {
            Write-FallbackPending $q $verdict $pending (Join-Path $notes "_solve-q$q-a$attempt.log")
        }
        $line = "Q{0} | {1} | {2}s | {3} | attempt={4} | {5}" -f `
            $q, $attemptProfile, $total, $verdict, $attempt, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Write-Host $line
        Add-Content -Path $solveLog -Value $line -Encoding UTF8
    }
}
finally {
    if (-not $DryRun) {
        if (-not $KeepMounted -and -not $SkipMount) {
            & $python "$bin\myos_mount.py" unmount *> $null
        }
        if (-not $SkipEvalGold) {
            & $python "$bin\eval_gold.py" 2>&1 | Out-String -Width 200 | Write-Output
        }
    }
}
