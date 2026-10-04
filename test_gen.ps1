
Add-Type -AssemblyName System.Speech
 = New-Object System.Speech.Synthesis.SpeechSynthesizer
.SetOutputToWaveFile('test_speech.wav')
.Speak('We will be doing a technical interview focused on Data Engineering.')
.Dispose()
