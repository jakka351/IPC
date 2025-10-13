import os
import struct
from pathlib import Path

KZB_HEADER = b'\x2eKZB'
FOLDER_SIZE = 4 + 2 +

headerlen = 101

def align4(size):
	"""Align a size to the next multiple of 4."""
	return (size + 3) & ~3

class Element:
	def __init__(self, name: str, data: bytes, unk1=0x3E8, unk2=0):
		self.name = name
		self.data = data
		self.unk1 = unk1
		self.unk2 = unk2
		self.addr = 0
		self.size = len(data)

class Folder:
	def __init__(self, name: str):
		self.name = name
		self.subfolders = []  # list[Folder]
		self.elements = []	# list[Element]
		self.size = 0		 # sum of contained file sizes

def collect_the_lot(currentdir: Path) -> Folder:
	thisfolder = Folder(os.path.basename(currentdir));

	for entry in os.scandir(currentdir):
		if entry.is_dir():
			newfolder = collect_the_lot(entry.path);
			thisfolder.subfolders.append(newfolder);
			thisfolder.size += newfolder.size;
		elif entry.is_file():
			with open(entry.path, 'rb') as file:
				data = file.read();
			newelement = Element(entry.name, data);
			thisfolder.elements.append(newelement);
			thisfolder.size += len(data);
	
	return thisfolder;

def print_folder(folder: Folder, indent=0):
	prefix = "  " * indent * 4
	print(f"{prefix}Folder: {folder.name} (size={folder.size})")

	indent += 1
	
	for sub in folder.subfolders:
		print_folder(sub, indent)
		
	# Print elements (files)
	for elem in folder.elements:
		print(f"{prefix}Element: {elem.name} (size={elem.size}, unk1={elem.unk1}, unk2={elem.unk2})")
	
	# Recursively print subfolders
	

def fill_out_buff(buf: bytearray, folder: Folder, isroot=False):
	if (isroot == False):
		buf += struct.pack('>IH', folder.size, len(folder.name));
		buf += folder.name.encode('utf-8');
		
		while (len(buf) % 4):
			buf += b'\x00';
		
		buf += struct.pack('>I', len(folder.subfolders));
	
	# if (len(folder.subfolders) > 0):
	# 	fill_out_buff(buf, subfolder);
	# else:
	# 	buf += struct.pack('>I', len(folder.elements));

	for subfolder in folder.subfolders:
		fill_out_buff(buf, subfolder);
	
	buf += struct.pack('>I', len(folder.elements));

	for element in folder.elements:
		buf += struct.pack('>IIIIH', element.addr, element.size, 0x3E8, 0, len(element.name)); #TODO: fix this need to calc header length and start allocating addrs
		buf += element.name.encode('utf-8');
		while (len(buf) % 4):
			buf += b'\x00';



def pack_kzb(inputfolder: Path):
	root_folder = collect_the_lot(inputfolder)
	
	file_buf = bytearray();
	file_buf += KZB_HEADER;
	file_buf += b'\x00' * 0x48;

	headerlen += len(root_folder.name);

	file_buf += struct.pack('>H', len(root_folder.name));
	file_buf += root_folder.name.encode('utf-8');
	while (len(file_buf) % 4):
		file_buf += b'\x00';
	file_buf += b'\x00' * 16; # UNKS PULL UP
	file_buf += struct.pack('>I', len(root_folder.subfolders));

	fill_out_buff(file_buf, root_folder, True);

	return file_buf;




if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Pack a folder into a KZB file")
	parser.add_argument("input_folder", type=Path, help="Folder to pack")
	parser.add_argument("output_file", type=Path, help="Output .kzb file")
	args = parser.parse_args()

	file_buf = pack_kzb(args.input_folder);
	with open(args.output_file, 'wb') as ootfile:
		ootfile.write(file_buf);
	print(f"Packed {args.input_folder} -> {args.output_file}")
