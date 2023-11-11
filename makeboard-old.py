#!/usr/bin/env python3
import os
import shutil
import configparser
import subprocess
import glob 
from string import Template
import hashlib

##################################################
# 1 . read config file and collect all information
###################################################

config_file = configparser.ConfigParser()
config_file.read('board_data/board-config.ini')
# build options dictionary
d = {}
for s in config_file.sections():
    for key, value in config_file[s].items():
        d[key]=value

        
#check for empty values
optional_keys =[]
for key, value in d.items():
    if (not value) and not  (key in optional_keys)  :
        print(f'No value provided for {key}')
        raise RuntimeError('Missing configuration parameters')
    
#define commonly used variables
board_name = d['board_name']    
version = d['package_version']

# add MCU-specific parameters
if d['chip_family'] == 'SAMD21':
    d['flash_size'] = 262144
    d['data_size'] =  0
    d['offset'] = '0x2000'
    d['build_mcu'] =  'cortex-m0plus'
    d['f_cpu'] =  '48000000L'
    d['extra_flags'] = '-DARDUINO_SAMD_ZERO -DARM_MATH_CM0PLUS'
    d['openocdscript'] =  'scripts/openocd/daplink_samd21.cfg'
    

elif d['chip_family'] == 'SAMD51' or d['chip_family'] == 'SAME51':
    d['flash_size'] = 507904 # SAMD51P20A and SAMD51J20A has 1032192
    d['data_size'] =  0
    d['offset'] = '0x4000'
    d['build_mcu'] =  'cortex-m4'
    d['f_cpu'] =  '120000000L'
    d['extra_flags'] = '-D__SAMD51__ -D__FPU_PRESENT -DARM_MATH_CM4 -mfloat-abi=hard -mfpu=fpv4-sp-d16'
    d['openocdscript'] =  'scripts/openocd/daplink_samd51.cfg'

else:
    raise RuntimeError('Invalid MCU family')

# fix flash size:
if d['chip_variant'] == 'SAMD51P20A' or d['chip_variant'] == 'SAMD51J20A':
    d['flash_size'] = 1032192

# add extra flags
chip_variant=d['chip_variant']

d['extra_flags'] += f' -D__{chip_variant}__'
if d['crystalless']:
    d['extra_flags'] += ' -DCRYSTALLESS'

# build Cache and Speed menus (SAMD51/SAME51 only)
d['menu_cache']=''
d['menu_speed']=''

if d['chip_family'] == 'SAMD51' or d['chip_family'] == 'SAME51':
    # cache menu 
    cache_prefix = f"{board_name}.menu.cache"
    d['menu_cache']+= f"{cache_prefix}.on = Enabled\n"
    d['menu_cache']+= f"{cache_prefix}.on.build.cache_flags=-DENABLE_CACHE\n"
    d['menu_cache']+= f"{cache_prefix}.off=Disabled\n"
    d['menu_cache']+= f"{cache_prefix}.off.build.cache_flags=\n"
    # speed menu 
    speed_prefix = f"{board_name}.menu.speed"
    d['menu_speed']+= f"{speed_prefix}.120=120 MHz (standard)\n"
    d['menu_speed']+= f"{speed_prefix}.120.build.f_cpu=120000000L\n"
    d['menu_speed']+= f"{speed_prefix}.150=150 MHz (overclock)\n"
    d['menu_speed']+= f"{speed_prefix}.150.build.f_cpu=150000000L\n"
    d['menu_speed']+= f"{speed_prefix}.180=180 MHz (overclock)\n"
    d['menu_speed']+= f"{speed_prefix}.180.build.f_cpu=180000000L\n"
    d['menu_speed']+= f"{speed_prefix}.200=200 MHz (overclock)\n"
    d['menu_speed']+= f"{speed_prefix}.200.build.f_cpu=200000000L\n"
                    
    
print("Successfully read config file")

##################################################
# 2. copy files to build directory
###################################################


# clean build directory if exists
if os.path.exists('build'):
    print("Removing old build directory")
    shutil.rmtree('build')
    
package_dir = f"build/{version}"
variants_dir = package_dir+'/variants'
board_variant = f"{variants_dir}/{board_name}"
print("Copying package template files to build directory")
shutil.copytree('PACKAGE_TEMPLATE',package_dir)
if d['chip_family'] == 'SAMD21':
    # rename one of template directories and delete two others
    shutil.move(variants_dir+'/TEMPLATE_SAMD21', board_variant)
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51')
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51P20A')

elif d['chip_variant'] == 'SAMD51P20A':
    shutil.move(variants_dir+'/TEMPLATE_SAMD51P20A', board_variant)
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51')
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD21')
else:
    #SAMD51, but not SAMD51P20A
    shutil.move(variants_dir+'/TEMPLATE_SAMD51', board_variant)
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD21')
    shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51P20A')

shutil.copy2('board_data/variant.cpp', board_variant)
shutil.copy2('board_data/variant.h', board_variant)

#now, copy bootloader source:
print("Copying bootloader source code to build directory")
shutil.copytree('uf2-samd21', 'build/uf2-samd21')

###################################################
# 3. build bootloader
###################################################
# first, create config files
bootloader_config_dir = f"build/uf2-samd21/boards/{board_name}"
os.mkdir(bootloader_config_dir)
print("Creating config files for the board bootloader")
# board.mk
with open(f"{bootloader_config_dir}/board.mk", 'w', encoding = 'UTF-8') as board_mk:
    board_mk.write("CHIP_FAMILY = "+d['chip_family'].lower()+"\n")
    board_mk.write("CHIP_VARIANT = "+d['chip_variant']+"\n")
# board_config.h
with open(bootloader_config_dir+'/board_config.h', 'w', encoding = 'UTF-8') as board_config:
    board_config.write("#ifndef BOARD_CONFIG_H\n")
    board_config.write("#define BOARD_CONFIG_H\n\n")
    board_config.write('#define VENDOR_NAME      "'+d['vendor_name_long']+'"\n')
    board_config.write('#define PRODUCT_NAME     "'+d['board_name_long']+'"\n')
    board_config.write('#define VOLUME_LABEL     "'+d['volume_label']+'"\n')
    board_config.write('#define INDEX_URL        "'+d['info_url']+'"\n\n')
    board_config.write('#define USB_VID          '+d['usb_vid']+'\n')
    board_config.write('#define USB_PID          '+d['usb_pid']+'\n')
    board_id = d['chip_variant']+"-"+d['board_define_name']+"-v0"
    board_config.write('#define BOARD_ID         "'+board_id+'"\n\n')
    if d['crystalless']:
        board_config.write('#define CRYSTALLESS      1\n\n')
    if 'led_pin' in d:
        board_config.write('#define LED_PIN          '+d['led_pin']+'\n\n')
    if 'neopixel_pin' in d:
        board_config.write('#define BOARD_NEOPIXEL_PIN   '+d['neopixel_pin']+'\n')
        board_config.write('#define BOARD_NEOPIXEL_COUNT 1\n\n')
    if d['chip_family'] == 'SAMD51' or d['chip_family'] == 'SAME51':
        usart_options = ['BOOT_USART_MODULE','BOOT_USART_MASK', 'BOOT_USART_BUS_CLOCK_INDEX',
                         'BOOT_USART_PAD_SETTINGS', 'BOOT_USART_PAD3', 'BOOT_USART_PAD2', 'BOOT_USART_PAD1',
                         'BOOT_USART_PAD0', 'BOOT_GCLK_ID_CORE', 'BOOT_GCLK_ID_SLOW']
        for key in usart_options:
            value = d[key.lower()]
            padded_key=key.ljust(27)
            board_config.write(f'#define {padded_key} {value}\n')
    board_config.write("#endif\n")
# get all paths for build tools 
new_env = os.environ.copy()
# find GCC included with Adafruit SAMD package
gcc_tool_path = new_env['HOME']+"/"+d['arduino15']+"/packages/adafruit/tools/arm-none-eabi-gcc"
# e.g. /Users/shurik/Library/Arduino15/packages/adafruit/tools/arm-none-eabi-gcc
if not os.path.exists(gcc_tool_path):
    raise RuntimeError("Couldn't find arm-none-eabi-gcc. Make sure you have installed Adafruit SAMD boards package!")
# now look for latest version.
# we do not use just listdir since we want to make sure we do not include dotfiles
gcc_versions = sorted(glob.glob(gcc_tool_path+"/*"))
last_gcc_version = gcc_versions[-1]
gcc_path = f"{last_gcc_version}/bin"
print(f"Found GCC compiler at {gcc_path}")
# add the paths to PATH env variable
if 'make_path' in d:
    new_env["PATH"] = os.pathsep.join([new_env["PATH"], gcc_path, d['make_path']])
else:
    new_env["PATH"] = os.pathsep.join([new_env["PATH"], gcc_path])
#print(new_env["PATH"])
os.chdir('build/uf2-samd21')
# run make to build bootloader
print("Starting GNU make...")
with open('bootloader_build_log.txt', 'w', encoding = 'UTF-8') as logfile:
    command = f"make BOARD={board_name} VERSION={version}"
    make_process = subprocess.run(command, shell = True, env=new_env, stdout=logfile,text=True)
    if (make_process.returncode):
        print("Making bootloader failed. Please see the log file for details")
    else:
        print("Successfully built bootloader")
        
# copy built bootloader
bootloader_dir = f"build/{board_name}"
bootloader_basename = f"bootloader-{board_name}-{version}"
print(f"Bootloader location: {bootloader_dir}/{bootloader_basename}.{{elf,bin}}")
bootloader_dest = f"../../{package_dir}/bootloaders/{board_name}"
os.mkdir(bootloader_dest)
shutil.copy(f"{bootloader_dir}/{bootloader_basename}.bin", bootloader_dest)
shutil.copy(f"{bootloader_dir}/{bootloader_basename}.elf", bootloader_dest)
os.chdir("../..")
# add bootloader filename to dictionary
d['bootloader_filename']=f"{bootloader_basename}.bin"
###################################################
# 4. create boards.txt file
###################################################
print("Creating boards.txt file")
with open(package_dir+'/boards_TEMPLATE.txt', 'r', encoding = 'UTF-8') as template_file:
    boards_template =template_file.read()

boards = Template(boards_template).safe_substitute(d)

with open(package_dir+'/boards.txt', "w", encoding = 'UTF-8') as boards_txt: 
    boards_txt.write(boards)

os.remove(package_dir+'/boards_TEMPLATE.txt')

###################################################
# 5. compress the package into an archive 
###################################################
zip_archive = shutil.make_archive(f"build/{board_name}-{version}", 'zip', package_dir)
archive_size = os.path.getsize(zip_archive)
# compute hash:
with open(zip_archive, "rb") as f:
    bytes = f.read() # read entire file as bytes
    hash = hashlib.sha256(bytes).hexdigest()
    
print(f"Created package archive, size {archive_size} bytes,\n SHA256 hash: {hash}")
# add the info to dictionary
d['archive_filename']=f"{board_name}-{version}.zip"
d['archive_size']= archive_size
d['archive_checksum']=hash 
###################################################
# 6. create index.json file
###################################################
print("Creating json index file")
with open('package_TEMPLATE_index.json', 'r', encoding = 'UTF-8') as template_file:
    index_template =template_file.read()

indexfile_content = Template(index_template).safe_substitute(d)
indexfile_name = "build/package_"+d['vendor_name']+"_index.json"
with open(indexfile_name, "w", encoding = 'UTF-8') as indexfile: 
    indexfile.write(indexfile_content)


    



   
