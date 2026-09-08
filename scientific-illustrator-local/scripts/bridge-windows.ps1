#requires -Version 5.1
[CmdletBinding()]
param([string]$ProgId='')
$ErrorActionPreference='Stop'
$utf8=New-Object Text.UTF8Encoding($false)
[Console]::InputEncoding=$utf8
[Console]::OutputEncoding=$utf8
$app=$null
try {
    if ($ProgId -and $ProgId -notmatch '^Illustrator\.Application(?:\.\d+)?$') { throw 'Invalid Illustrator ProgID' }
    $running=@(Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -match '^Illustrator'})
    if ($running.Count -eq 0) { throw 'Open Illustrator yourself; this adapter only attaches to a running instance.' }
    if ($running.Count -gt 1 -and -not $ProgId) { throw 'Multiple Illustrator processes are open; select the registered version with --prog-id.' }
    $ids=@('Illustrator.Application')
    if ($ProgId) { $ids=@($ProgId) } else {
        $registered=@(Get-ChildItem 'Registry::HKEY_CLASSES_ROOT' -ErrorAction SilentlyContinue |
            Where-Object {$_.PSChildName -match '^Illustrator\.Application\.\d+$'} |
            Sort-Object { [int]($_.PSChildName.Split('.')[-1]) } -Descending |
            ForEach-Object {$_.PSChildName})
        $ids += $registered
    }
    foreach ($id in $ids) {
        try { $app=[Runtime.InteropServices.Marshal]::GetActiveObject($id);break } catch { }
    }
    if ($null -eq $app) { throw 'Cannot attach to Illustrator COM. Use Windows PowerShell 5.1 in the same logged-in user session.' }
    while ($null -ne ($line=[Console]::ReadLine())) {
        try {
            $request=ConvertFrom-Json -InputObject $line
            $result=[string]$app.DoJavaScript([string]$request.script)
            $response=@{ok=$true;result=$result} | ConvertTo-Json -Compress
        } catch { $response=@{ok=$false;error=$_.Exception.Message} | ConvertTo-Json -Compress }
        [Console]::WriteLine($response)
    }
} catch {
    [Console]::WriteLine((@{ok=$false;error=$_.Exception.Message} | ConvertTo-Json -Compress))
    exit 2
} finally {
    if ($null -ne $app) { [Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null }
}
