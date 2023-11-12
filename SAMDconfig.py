"""
Main class to keep configuration data for SAMD board
* Author(s): Alexander Kirillov
* Version: 4.0
"""

import os
import shutil
import configparser
import subprocess
import glob 
from string import Template
import hashlib

class SAMDconfig:
    # constructor
    def __init__(self, filename):
        # dictionary containign all config data 
        self.d = {}
        # read all values from config file 
        config_file = configparser.ConfigParser()
        config_file.read(filename)
        for s in config_file.sections():
            for key, value in config_file[s].items():
                self.d[key]=value

        #check for empty values
        for key, value in self.d.items():
            if (not value):
                print(f'No value provided for {key}')
                raise RuntimeError('Missing configuration parameters')
            
        #define common properties 
        self.name = self.d['board_name']
        self.version = self.d['package_version']
        self.chip_family = self.d['chip_family']
        self.chip_variant = self.d['chip_variant']
        self.is_samd51 = (self.d['chip_family'] == 'SAMD51') or (self.d['chip_family'] == 'SAME51')

        # add MCU-specific parameters
        if self.d['chip_family'] == 'SAMD21':
            self.d['flash_size'] = 262144
            self.d['data_size'] =  0
            self.d['offset'] = '0x2000'
            self.d['build_mcu'] =  'cortex-m0plus'
            self.d['f_cpu'] =  '48000000L'
            self.d['extra_flags'] = '-DARDUINO_SAMD_ZERO -DARM_MATH_CM0PLUS'
            self.d['openocdscript'] =  'scripts/openocd/daplink_samd21.cfg'
        elif self.is_samd51:
            self.d['flash_size'] = 507904 # SAMD51P20A and SAMD51J20A has 1032192
            self.d['data_size'] =  0
            self.d['offset'] = '0x4000'
            self.d['build_mcu'] =  'cortex-m4'
            self.d['f_cpu'] =  '120000000L'
            self.d['extra_flags'] = '-D__SAMD51__ -D__FPU_PRESENT -DARM_MATH_CM4 -mfloat-abi=hard -mfpu=fpv4-sp-d16'
            self.d['openocdscript'] =  'scripts/openocd/daplink_samd51.cfg'
        else:
            raise RuntimeError('Invalid MCU family')

        # fix flash size:
        if self.chip_variant == 'SAMD51P20A' or self.chip_variant == 'SAMD51J20A':
            self.d['flash_size'] = 1032192

        # add extra flags
        self.d['extra_flags'] += f' -D__{self.chip_variant}__'
        if self.d['crystalless']:
            self.d['extra_flags'] += ' -DCRYSTALLESS'


    # reads template file, does all substitutions from the dictionary, saves result as destination
    # source and destination shoudl be filenames 
    def process_file(self, source, destination):

        with open(source, 'r', encoding = 'UTF-8') as template_file:
            original  =template_file.read()
            
        new_data = Template(original).substitute(self.d)
        with open(destination, "w", encoding = 'UTF-8') as dest_file: 
            dest_file.write(new_data)

    def setup_build_directory(self, dirname):
        self.build_directory = dirname
        self.package_directory = f"{dirname}/{self.version}"
        if os.path.exists(dirname):
            print("Removing old build directory")
            shutil.rmtree(dirname)
        shutil.copytree('PACKAGE_TEMPLATE',self.package_directory)
        shutil.copytree('uf2-samd21', f'{self.build_directory}/uf2-samd21')
        # now, select which board template to use - thye have different link scripts
        variants_dir = self.package_directory+"/variants"
        board_variant = f"{variants_dir}/{self.name}"
        if self.chip_family == 'SAMD21':
            # rename one of template directories and delete two others
            shutil.move(variants_dir+'/TEMPLATE_SAMD21', board_variant)
            shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51')
            shutil.rmtree(variants_dir+'/TEMPLATE_SAMD51P20A')

        elif self.chip_variant == 'SAMD51P20A':
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

    # creates boards.txt file in given directory, by processing boards_TEMPLATE.txt in that directory 
    def write_boards_txt(self):
        # if necessary, add entries for cache and speed menus 
        self.d['menu_cache']=''
        self.d['menu_speed']=''
        if self.is_samd51:
            # cache menu 
            cache_prefix = f"{self.name}.menu.cache"
            self.d['menu_cache']+= f"{cache_prefix}.on = Enabled\n"
            self.d['menu_cache']+= f"{cache_prefix}.on.build.cache_flags=-DENABLE_CACHE\n"
            self.d['menu_cache']+= f"{cache_prefix}.off=Disabled\n"
            self.d['menu_cache']+= f"{cache_prefix}.off.build.cache_flags=\n"
            # speed menu 
            speed_prefix = f"{self.name}.menu.speed"
            self.d['menu_speed']+= f"{speed_prefix}.120=120 MHz (standard)\n"
            self.d['menu_speed']+= f"{speed_prefix}.120.build.f_cpu=120000000L\n"
            self.d['menu_speed']+= f"{speed_prefix}.150=150 MHz (overclock)\n"
            self.d['menu_speed']+= f"{speed_prefix}.150.build.f_cpu=150000000L\n"
            self.d['menu_speed']+= f"{speed_prefix}.180=180 MHz (overclock)\n"
            self.d['menu_speed']+= f"{speed_prefix}.180.build.f_cpu=180000000L\n"
            self.d['menu_speed']+= f"{speed_prefix}.200=200 MHz (overclock)\n"
            self.d['menu_speed']+= f"{speed_prefix}.200.build.f_cpu=200000000L\n"
        
        # substitute all values in the template board.txt file
        self.process_file(f"{self.package_directory}/boards_TEMPLATE.txt", f"{self.package_directory}/boards.txt")
        os.remove(f"{self.package_directory}/boards_TEMPLATE.txt")       

    # creates board.mk file in given directory
    def write_board_mk(self, dest_directory):
        with open(f"{dest_directory}/board.mk", 'w', encoding = 'UTF-8') as board_mk:
            board_mk.write("CHIP_FAMILY = "+ self.d['chip_family'].lower()+"\n")
            board_mk.write("CHIP_VARIANT = "+self.d['chip_variant']+"\n")

    #creates board_config.h gile in given directory 
    def write_board_config(self, dest_directory):
        with open(f"{dest_directory}/board_config.h", 'w', encoding = 'UTF-8') as board_config:
            board_config.write("#ifndef BOARD_CONFIG_H\n")
            board_config.write("#define BOARD_CONFIG_H\n\n")
            board_config.write('#define VENDOR_NAME      "'+self.d['vendor_name_long']+'"\n')
            board_config.write('#define PRODUCT_NAME     "'+self.d['board_name_long']+'"\n')
            board_config.write('#define VOLUME_LABEL     "'+self.d['volume_label']+'"\n')
            board_config.write('#define INDEX_URL        "'+self.d['info_url']+'"\n\n')
            board_config.write('#define USB_VID          '+self.d['usb_vid']+'\n')
            board_config.write('#define USB_PID          '+self.d['usb_pid']+'\n')
            board_id = self.chip_variant+"-"+self.d['board_define_name']+"-v0"
            board_config.write('#define BOARD_ID         "'+board_id+'"\n\n')
            if self.d['crystalless']:
                board_config.write('#define CRYSTALLESS      1\n\n')
            if 'led_pin' in self.d:
                board_config.write('#define LED_PIN          '+self.d['led_pin']+'\n\n')
            if 'neopixel_pin' in self.d:
                board_config.write('#define BOARD_NEOPIXEL_PIN   '+self.d['neopixel_pin']+'\n')
                board_config.write('#define BOARD_NEOPIXEL_COUNT 1\n\n')
            if self.is_samd51:
                usart_options = ['BOOT_USART_MODULE','BOOT_USART_MASK', 'BOOT_USART_BUS_CLOCK_INDEX',
                                'BOOT_USART_PAD_SETTINGS', 'BOOT_USART_PAD3', 'BOOT_USART_PAD2', 'BOOT_USART_PAD1',
                                'BOOT_USART_PAD0', 'BOOT_GCLK_ID_CORE', 'BOOT_GCLK_ID_SLOW']
                for key in usart_options:
                    value = self.d[key.lower()]
                    padded_key=key.ljust(27)
                    board_config.write(f'#define {padded_key} {value}\n')
            board_config.write("#endif\n")

    # gets all necessary paths for GCC and make and adds them to PATH
    # returns environment with these paths
    def get_paths(self):
        new_env = os.environ.copy()
        # find GCC included with Adafruit SAMD package
        gcc_tool_path = new_env['HOME']+"/"+self.d['arduino15']+"/packages/adafruit/tools/arm-none-eabi-gcc"
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
        if 'make_path' in self.d:
            new_env["PATH"] = os.pathsep.join([new_env["PATH"], gcc_path, self.d['make_path']])
        else:
            new_env["PATH"] = os.pathsep.join([new_env["PATH"], gcc_path])
        return(new_env)

    def build_bootloader(self):
        # first, get paths 
        new_env = self.get_paths()
        os.chdir('build/uf2-samd21')
        # run make to build bootloader
        print("Starting GNU make...")
        with open('bootloader_build_log.txt', 'w', encoding = 'UTF-8') as logfile:
            command = f"make BOARD={self.name} VERSION={self.version}"
            make_process = subprocess.run(command, shell = True, env=new_env, stdout=logfile,text=True)
            if (make_process.returncode):
                print("Making bootloader failed. Please see the log file for details")
            else:
                print("Successfully built bootloader")
        
        # copy built bootloader
        os.chdir("../..")
        bootloader_dir = f"build/uf2-samd21/build/{self.name}"
        bootloader_basename = f"bootloader-{self.name}-{self.version}"
        return(bootloader_dir,bootloader_basename)
    