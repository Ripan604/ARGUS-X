$ErrorActionPreference = 'Stop'
$taskWorkspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$taskOutput = Join-Path $taskWorkspace 'output\release'
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskCompiler = (Get-Command g++ -ErrorAction Stop).Source
$taskProtocolBinary = Join-Path $taskOutput 'probe-protocol-tests.exe'
$taskSketchBinary = Join-Path $taskOutput 'probe-sketch-tests.exe'
& $taskCompiler -std=c++17 -Wall -Wextra -Werror -pedantic (Join-Path $PSScriptRoot 'protocol_test.cpp') -o $taskProtocolBinary
if ($LASTEXITCODE -ne 0) { throw 'Portable protocol compilation failed' }
& $taskCompiler -std=c++17 -Wall -Wextra -Werror -pedantic "-I$PSScriptRoot" (Join-Path $PSScriptRoot 'sketch_test.cpp') -o $taskSketchBinary
if ($LASTEXITCODE -ne 0) { throw 'Full sketch mock compilation failed' }
& $taskProtocolBinary
if ($LASTEXITCODE -ne 0) { throw 'Portable protocol properties failed' }
& $taskSketchBinary (Join-Path $taskOutput 'probe-v2-host-fixture.txt')
if ($LASTEXITCODE -ne 0) { throw 'Full sketch mock tests failed' }
Write-Output 'These are host/mock results. No board target or physical timing was validated.'
