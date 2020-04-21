import donut
import shutil


async def donut_handler(services, args):
    print('This is where we would configure things to properly handle a .donut file request.')
    name = args.get('file')
    basename, extension = name.split('.')
    # Currently just generates sellcode from the demo file and saves it as the payload "shellcode.bin"
    # Then the agent reads that file with the hardcoded name and executes the shellcode
    file_name = r'/Users/amanners/MITRE_Projects/caldera/plugins/builder/payloads/%s' % name
    dst = r'/Users/amanners/MITRE_Projects/caldera/plugins/builder/payloads/%s.exe' % basename
    shutil.move(src=file_name, dst=dst)
    shellcode = donut.create(file=dst)

    print("DEBUG: Shellcode length: ")

    #Format the shellcode how the shellcode executor expects it
    #hexbytes = shellcode.hex()

    #final = ""

    #for i in range(0, len(hexbytes), 2):
     #final += ('0x' + hexbytes[i:i + 2] + ',')

    #remove the final comma
    #final = final[:-1]

    #final should now contain the shellcode
    #outfile = open("shellcode.hex", "wb")
    #outfile.write(final)
    #outfile.close()

    try:
        with open(file_name, 'wb') as f:
            f.write(shellcode)
    except Exception as ex:
        print(ex)
    return '%s' % name, '%s' % name
