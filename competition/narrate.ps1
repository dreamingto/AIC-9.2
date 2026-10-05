$ErrorActionPreference='Stop'
$outputRoot=Join-Path (Split-Path $PSScriptRoot -Parent) 'output/competition'
$audioRoot=Join-Path $outputRoot 'audio'
New-Item -ItemType Directory -Force -Path $audioRoot | Out-Null
$slides=Get-Content -LiteralPath (Join-Path $outputRoot 'narration.json') -Raw -Encoding utf8 | ConvertFrom-Json
$voice=New-Object -ComObject SAPI.SpVoice
$token=@($voice.GetVoices() | Where-Object { $_.GetDescription() -like '*Huihui*' })[0]
if(!$token) { throw '需要本机中文 Huihui SAPI 语音。' }
$voice.Voice=$token
$voice.Rate=4
for($i=0;$i -lt $slides.Count;$i++) {
  $stream=New-Object -ComObject SAPI.SpFileStream
  $stream.Open((Join-Path $audioRoot ('part-'+($i+1)+'.wav')),3,$false)
  $voice.AudioOutputStream=$stream
  [void]$voice.Speak($slides[$i].notes)
  $stream.Close()
  Write-Output ('narrated '+($i+1)+'/'+$slides.Count)
}
