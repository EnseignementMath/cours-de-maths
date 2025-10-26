Option Explicit

Function CellText(oCell As Object) As String
    If IsNull(oCell) Then
        CellText = ""
    Else
        CellText = Trim(oCell.getString())
    End If
End Function

Sub ExporterSelectionVersJSON()
    Dim oDoc, oSel, oRange, oSheet, aAddr, r As Long, c As Long
    Dim rows As Long, cols As Long
    Dim headers() As String
    Dim dataJSON As String
    
    oDoc = ThisComponent
    oSel = oDoc.getCurrentSelection()
    If oSel.supportsService("com.sun.star.sheet.SheetCellRange") = False Then
        MsgBox "Sélectionne d’abord un bloc rectangulaire (avec l’en-tête).", 48, "Export sélection"
        Exit Sub
    End If
    
    oRange = oSel
    aAddr = oRange.getRangeAddress()
    oSheet = oDoc.Sheets.getByIndex(aAddr.Sheet)
    
    rows = aAddr.EndRow - aAddr.StartRow + 1
    cols = aAddr.EndColumn - aAddr.StartColumn + 1
    If rows < 2 Or cols < 1 Then
        MsgBox "La sélection doit contenir au moins une ligne d’en-tête et une ligne de données.", 48, "Export sélection"
        Exit Sub
    End If
    
    ReDim headers(cols - 1)
    For c = 0 To cols - 1
        headers(c) = LCase(Trim(oSheet.getCellByPosition(aAddr.StartColumn + c, aAddr.StartRow).getString()))
    Next c
    
    dataJSON = "["
    Dim rowJSON As String
    For r = aAddr.StartRow + 1 To aAddr.EndRow
        rowJSON = "{"
        For c = 0 To cols - 1
            Dim key As String, val As String
            key = headers(c)
            val = Replace(oSheet.getCellByPosition(aAddr.StartColumn + c, r).getString(), """", """")
            rowJSON = rowJSON & """" & key & """: """ & Trim(val) & """"
            If c < cols - 1 Then rowJSON = rowJSON & ", "
        Next c
        rowJSON = rowJSON & "}"
        dataJSON = dataJSON & rowJSON
        If r < aAddr.EndRow Then dataJSON = dataJSON & ", "
    Next r
    dataJSON = dataJSON & "]"
    
    Dim tmpDir As String, outPath As String
    tmpDir = Environ("TEMP")
    If Right(tmpDir, 1) = "" Or Right(tmpDir, 1) = "/" Then
        outPath = tmpDir & "cahier_selection.json"
    Else
        outPath = tmpDir & Chr(92) & "cahier_selection.json"
    End If
    
    Dim f As Integer
    f = FreeFile
    Open outPath For Output As #f
    Print #f, dataJSON
    Close #f
    
    MsgBox "Export JSON ok : " & outPath, 64, "Export sélection"
    
    ' Option : lancer le script Python automatiquement (adapter chemin Python + repo)
    'Dim cmd As String
    'cmd = """" & "C:\Python312\python.exe" & """" & " " & """" & "C:\Sites\cours-de-maths\publish_selection.py" & """"
    'Shell(cmd, 1)
End Sub
