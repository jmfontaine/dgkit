Output demo.gif

Set FontSize 16
Set Height 200
Set LineHeight 1.3
Set Padding 20
Set Shell bash
Set TypingSpeed 50ms
Set Width 900

Type "dgkit convert -f jsonl releases.xml.gz"
Enter
Sleep 5s
Hide
Ctrl+C
Sleep 1s
Show
Enter

Type "dgkit load --dsn discogs.db releases.xml.gz"
Enter
Sleep 5s
Hide
Ctrl+C
Sleep 1s
Show
