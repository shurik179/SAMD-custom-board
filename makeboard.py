#!/usr/bin/env python3
import SAMDconfig
import os
import shutil
import hashlib 



# Read all board configuration data 
print("Reading board config...")
board = SAMDconfig.SAMDconfig("board_data/board-config.ini")

# setup buidl directory and move there all source files     
print("Copying sources to build directory...")
board.setup_build_directory('build')

# write config files for bootloader 
print("Creating config files for the board bootloader")
bootloader_config_dir = f"build/uf2-samd21/boards/{board.name}"
os.mkdir(bootloader_config_dir)
board.write_board_mk(bootloader_config_dir)
board.write_board_config(bootloader_config_dir)

# build bootloader 
print("Building bootloader...")
bootloader_dir, bootloader_basename = board.build_bootloader()
print("Bootloader uccessfully built")

# copy built bootloader into the package 
bootloader_dest = f"{board.package_directory}/bootloaders/{board.name}"
os.mkdir(bootloader_dest)
shutil.copy(f"{bootloader_dir}/{bootloader_basename}.bin", bootloader_dest)
shutil.copy(f"{bootloader_dir}/{bootloader_basename}.elf", bootloader_dest)

# add bootloader filename to dictionary
board.d['bootloader_filename']=f"{bootloader_basename}.bin"

# create boards.txt
print("Writing boards.txt file")
board.write_boards_txt()


#compressing directory into zip archive 
zip_archive = shutil.make_archive(f"build/{board.name}-{board.version}", 
                                  'zip', 
                                  root_dir = 'build',
                                  base_dir=board.version)
archive_size = os.path.getsize(zip_archive)
# compute hash:
with open(zip_archive, "rb") as f:
    bytes = f.read() # read entire file as bytes
    hash = hashlib.sha256(bytes).hexdigest()
    
print(f"Created package archive, size {archive_size} bytes,\n SHA256 hash: {hash}")
# add the info to dictionary
board.d['archive_filename']=f"{board.name}-{board.version}.zip"
board.d['archive_size']= archive_size
board.d['archive_checksum']=hash 

# create json file 
print("Creating json index file")
indexfile_name = "build/package_"+board.d['vendor_name']+"_index.json"
board.process_file('package_TEMPLATE_index.json', indexfile_name)
