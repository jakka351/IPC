# VBF File Packing/Unpacking Process.

The `VBF` File format uses `LZSS` compression, there is a `C++` and a `C#` implementation of `LZSS` in this folder.     

`Thanks Roland`  

## Re-Packing. 
Repacking will look something lioe this ->

binary file group -> LZSS compressed in correct order -> header added to compressed blob -> `vbf`
