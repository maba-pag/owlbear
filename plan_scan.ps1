$pr=@{critical=0;needed=1;important=2;'nice-to-have'=3;someday=4}
$sr=@{done=0;docs=1;review=2;'in-progress'=3;todo=4;backlog=5;ideation=6}
$raw = kanban\kanban-md.exe list --json --unblocked --not-blocked --unclaimed --status ideation,backlog,todo,in-progress,review,docs,done 2>&1 | Out-String
$tasks = $raw | ConvertFrom-Json
$tasks | Sort-Object {$pr[$_.priority]},{$sr[$_.status]} | ForEach-Object { 
  $w=@()
  if ($_.status -eq 'in-progress' -and $_.body -notmatch '## Test-Writer Notes') {$w+='TW:MISSING'}
  if ($_.status -in @('todo','in-progress','review','docs','done') -and $_.body -notmatch '(?m)^\s*(-\s|\d+\.\s)') {$w+='AC:MISSING'}
  if ($_.body -match 'Needs decomposition:') {$w+='DECOMP'}
  "$($_.id),$($_.status),$($_.priority),$($w -join ';')"
} | Out-File board_scan.csv -Encoding UTF8
