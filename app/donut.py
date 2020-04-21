import donut
import os
import shutil


async def donut_handler(services, args):
    _, file_name = await services.get('file_svc').find_file_path(args.get('file'), location='payloads')
    dir_path, donut_ext = os.path.split(file_name)
    exe_path = os.path.join(dir_path, '%s.exe' % donut_ext.split('.')[0])
    shutil.move(src=file_name, dst=exe_path)
    shellcode = donut.create(file=exe_path)
    try:
        with open(file_name, 'wb') as f:
            f.write(shellcode)
    except Exception as ex:
        print(ex)
    os.remove(exe_path)
    return '%s' % donut_ext, '%s' % donut_ext
