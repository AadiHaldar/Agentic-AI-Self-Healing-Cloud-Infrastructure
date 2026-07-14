[xml]$doc = Get-Content -Raw "temp_docx\word\document.xml"
$ns = New-Object Xml.XmlNamespaceManager($doc.NameTable)
$ns.AddNamespace("w","http://schemas.openxmlformats.org/wordprocessingml/2006/main")
$nodes = $doc.SelectNodes("//w:t", $ns)
$text = ""
foreach ($n in $nodes) { $text += $n.InnerText + " " }
$text | Out-File -Encoding utf8 "docx_full_text.txt"
