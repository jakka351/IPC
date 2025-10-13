# KZB File Format
## Better documentation coming soon™


NOTE: ALIGN SEEMS TO ADD 4 IF ALREADY ALLIGNED TO 4 BYTES, EXAMPLE: 4byte align 7cc8 = 7ccc]<br>
NOTE NOTE: IGNORE ABOVE SEEMS TO ONLY HAPPEN ONCE OR YOU WERE HALUCINATING


[NOBODY CARES BYTES][0x4c]]<br>
[Root name len][2]]<br>
[Root name str][LEN]]<br>
(4byte align after root name str)]<br>
[UNK][4]]<br>
[UNK][4]]<br>
[UNK][4]]<br>
[UNK (seems to always be 0)][4]]<br>
[Folders in root count][4]]<br>

Folder:]<br>
[Folder size][4]<br>
[Folder name len][2]]<br>
[Folder name][LEN]]<br>
(4byte align after root name str)]<br>
[Sub folder count][4]]<br>
[Folder file count][4] // Little guesswork here but this is used if [Folder count] above is 0, assumption is that this is the last folder in a dir tree]<br>

Folder with sub (Sub folder count > 0):]<br>
[Folder size][4]]<br>
[Folder name len][2]]<br>
[Folder name][LEN]]<br>
(4byte align after root name str)]<br>
[Sub folder count][4]]<br>
[[FOLDER STRUCTURE]]]<br>


Elements:]<br>
[Element addr][4]]<br>
[Element size][4]]<br>
[UNK 1][4]]<br>
[UNK 2][4]]<br>
[Element name len][2]]<br>
[Element name][LEN]]<br>
(4byte align before next element)]<br>
