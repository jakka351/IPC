# `bitmaps.bin` extraction process with `dumpifs`

## `dumpifs`
`dumpifs` was built in `Windows Subsystem for Linux` from https://github.com/ttepatti/dumpifs-linux, it was then used to dump the filesystem from the binary file.  
```
jakka@jakka351:~/brute/_bitmaps.bin.extracted/dumpifs-linux$ dumpifs ~/bitmaps.bin
   Offset     Size  Name
        0       5c  Image-header
       5c      114  Image-directory
     ----     ----  Root-dirent
      170  314b5f8  install/bin/cluster.kzb
  314b768    7581e  install/bin/cluster.kzb.txt
  31c0f86       33  part_number/ifs3_part_number.txt
  31c0fb9        d  install/bin/cluster.kzb.cfg
Checksums: image=0x1b229b4
Image startup_size: 0 (0x0)
Image stored_size: 0 (0x0)
Compressed size: -4 (0xfffffffc)
```  

Looks promising, lets see what we can get out of it.  
`./dumpifs -b -x -d ~/ ~/bitmaps.bin`  
  
Outputs:  
```
jakka@jakka351:~/brute/_bitmaps.bin.extracted/dumpifs-linux$ ./dumpifs -b -x -d ~/ ~/bitmaps.bin
cluster.kzb ... size 51688952
cluster.kzb.txt ... size 481310
ifs3_part_number.txt ... size 51
cluster.kzb.cfg ... size 13
```  

