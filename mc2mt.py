#!/usr/bin/env python3

import os, sys, math, json
import shutil
import argparse
import tempfile
import zipfile

from PIL import Image

minecraft_version = "1.11"
minecraft_texpack = "Minecraft"

if (sys.platform == "win32"):
    pass # to do: see how to get Windows user folder
elif (sys.platform == "darwin"):
    pass # to do: ditto for mac
elif (sys.platform == "linux"):
    minecraft_dir = os.path.join(os.path.expanduser('~'), ".minecraft/versions")
    minetest_dir = os.path.join(os.path.expanduser('~'), ".minetest")

minetest_texdir = os.path.join(minetest_dir, "textures", minecraft_texpack)

asset_list = "filelist-1_11.json"

def eprint(*args, **kwargs): # print() to stderr
    print(*args, file=sys.stderr, **kwargs)

def print_if_true(bool_arg, *args, **kwargs): # only prints if true.
    if (bool_arg):
        print(*args, **kwargs)

def setup_argparse():
    parser = argparse.ArgumentParser(description='Convert Minecraft textures and assets for use in Minetest.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p','--progress', action='store_true', help='show informational progress bars. (requires tqdm)')
    group.add_argument('-q','--quiet', action='store_true', help='show no output except errors')
    group.add_argument('-v','--verbose', action='store_true', help='show detailed output of what is happening')

    return parser.parse_args()

def unpack_assets(jar_path, out_path):
    if not zipfile.is_zipfile(jar_path):
        eprint("Invalid jar file specified:", jar_path)
        sys.exit(1)
    
    minecraft_jar = zipfile.ZipFile(jar_path, "r")
    file_infolist = minecraft_jar.infolist()
    file_count = len(file_infolist)

    if script_args.progress:
        pbar = tqdm.tqdm(total=file_count)
        name_length_list = []
        for entry in file_infolist:
            name_length_list.append(len(os.path.basename(entry.filename)))
        pbar_desc_padding = max(name_length_list)
    

    for entry in file_infolist:
        data = minecraft_jar.read(entry.filename)
        full_path = os.path.join(out_path, entry.filename)
        s_path, s_name = os.path.split(full_path)
        if not os.path.exists(s_path):
            os.makedirs(s_path)
        file_out = open(full_path, 'wb')
        file_out.write(data)
        file_out.close()

        if script_args.progress:
            pbar.desc = s_name.ljust(pbar_desc_padding)
            pbar.update(1)
        
        if script_args.verbose:
            percent = math.floor(((file_infolist.index(entry)+1)/file_count)*100)
            print("[%3i%%] %s" % (percent, full_path))

def extract_assets(asset_list_path, in_path, out_path):
    asset_list = json.load(open(asset_list_path, "r"))
    file_count = len(asset_list["textures"])

    if script_args.progress:
        pbar = tqdm.tqdm(total=file_count)
        name_length_list = []
        for entry in asset_list["textures"]:
            name_length_list.append(len(entry["in_file"]))
        pbar_desc_padding = max(name_length_list)

    for texture_info in asset_list["textures"]:
        #print(texture_info)
        tmp_tex = None

        if ("in_file" not in texture_info):
            eprint("Texture missing in_file name:", texture_info)
            sys.exit(1)
        
        if ("out_file" not in texture_info):
            eprint("Texture missing out_file name:", texture_info)
            sys.exit(1)
        if (type(texture_info["in_file"]) != list): # I'll handle this case later.
            if ("crop" in texture_info):
                if tmp_tex is None:
                    tmp_tex = Image.open(os.path.join(in_path, texture_info["in_file"]))
                area = texture_info["crop"]
                tmp_tex = tmp_tex.crop((area[0], area[1], area[0]+area[2], area[1]+area[3]))
            if ("flip_x" in texture_info) and (texture_info["flip_x"]):
                if tmp_tex is None:
                    tmp_tex = Image.open(os.path.join(in_path, texture_info["in_file"]))
                tmp_tex = tmp_tex.transpose(Image.FLIP_LEFT_RIGHT)
            if ("flip_y" in texture_info) and (texture_info["flip_y"]):
                if tmp_tex is None:
                    tmp_tex = Image.open(os.path.join(in_path, texture_info["in_file"]))
                tmp_tex = tmp_tex.transpose(Image.FLIP_TOP_BOTTOM)
            if ("rotate" in texture_info) and (texture_info["rotate"] != 0):
                if tmp_tex is None:
                    was_open = False
                    tmp_tex = Image.open(os.path.join(in_path, texture_info["in_file"]))
                if texture_info["rotate"] == 90:
                    tmp_tex = tmp_tex.transpose(Image.ROTATE_90)
                elif texture_info["rotate"] == 180:
                    tmp_tex = tmp_tex.transpose(Image.ROTATE_180)
                elif texture_info["rotate"] == 270:
                    tmp_tex = tmp_tex.transpose(Image.ROTATE_270)
                else: # Invalid rotation: copy file instead
                    eprint("Invalid rotation in file '%s': %i" % (texture_info["in_file"], texture_info["rotate"]))
                    if was_open == False:
                        tmp_tex.close()
                        tmp_tex = None

        if tmp_tex is None: # None of the above operations occured
            try:
                shutil.copy(os.path.join(in_path, texture_info["in_file"]), os.path.join(out_path, texture_info["out_file"]))
                #print("Copied file '%s' to '%s'" % (texture_info["in_file"], os.path.join(out_path, texture_info["out_file"])))
            except OSError as e:
                eprint("Error while copying file '%s'\n%s" % (texture_info["in_file"], e))
                #sys.exit(1)
        else:
            try:
                tmp_tex.save(os.path.join(out_path, texture_info["out_file"]))
            except IOError as e:
                eprint("Error while saving file '%s'\n%s" % (texture_info["in_file"], e))
            finally:
                tmp_tex.close()

        if script_args.progress:
            pbar.desc = texture_info["in_file"].ljust(pbar_desc_padding)
            pbar.update(1)

        if script_args.verbose:
            percent = math.floor(((asset_list["textures"].index(texture_info)+1)/file_count)*100)
            print("[%3i%%] %s" % (percent, texture_info["in_file"]))

if __name__ == "__main__":
    script_args = setup_argparse()
    if script_args.progress:
        try:
            import tqdm
        except ImportError:
            eprint("The progress bar requires tqdm. Exiting...")
            sys.exit(1)

    print_if_true(not script_args.quiet, "Creating texture directory:", minetest_texdir)
    try:
        os.mkdir(minetest_texdir)
    except FileExistsError:
        print_if_true(not script_args.quiet, "Texture directory already exists. Skipping...")

    mctomt_tempdir = tempfile.TemporaryDirectory(prefix="mc2mt-")
    print_if_true(not script_args.quiet, "Created temporary directory:", mctomt_tempdir.name)

    print_if_true(not script_args.quiet, "Extracting jar...")
    unpack_assets(os.path.join(minecraft_dir, minecraft_version, minecraft_version + ".jar"), mctomt_tempdir.name)
    print_if_true(not script_args.quiet, "Extraction complete.")

    print_if_true(not script_args.quiet, "Converting assets...")
    extract_assets(asset_list, os.path.join(mctomt_tempdir.name, "assets/minecraft/textures"), minetest_texdir)
    print_if_true(not script_args.quiet, "Conversion complete.")

    mctomt_tempdir.cleanup()
    print_if_true(not script_args.quiet, "Your textures can be found at \"%s\"" % (minetest_texdir))
