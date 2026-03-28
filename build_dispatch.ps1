$candidates = (Get-Content board_scan.csv | ConvertFrom-Csv -Header id,status,priority,flags)
$dispatch = @()
$agent_map = @{
  'ideation' = 'researcher'
  'backlog' = 'architect'
  'todo' = 'test-writer'
  'in-progress' = 'builder'
  'review' = 'reviewer'
  'docs' = 'writer'
  'done' = 'auditor'
}

foreach ($c in $candidates) {
  $id = [int]$c.id
  $status = $c.status
  $flags = $c.flags
  
  # Gate 4: Skip TW:MISSING on in-progress
  if ($status -eq 'in-progress' -and $flags -like '*TW:MISSING*') {
    continue
  }
  
  # Gate 5: Skip AC:MISSING on todo+
  if ($status -in @('todo','in-progress','review','docs','done') -and $flags -like '*AC:MISSING*') {
    continue
  }
  
  # Map to agent
  $agent = $agent_map[$status]
  
  # Add to dispatch (cap at 20)
  if ($dispatch.Count -lt 20) {
    $dispatch += @{id = $id; agent = $agent}
  }
}

$json_dispatch = @{dispatch = $dispatch} | ConvertTo-Json -Compress
Write-Output $json_dispatch | Out-File final_dispatch.json -Encoding UTF8
