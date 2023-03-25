# IDA-RPyC

An IDA plugin that allows you call IDA python APIs from remote.

## 1. How to use

1. Install `rpyc`:
   
   ```shell
   $ pip install rpyc
   ```

2. Copy the script `ida-rpyc.py` to `<IDA install directory>\plugins`.

3. Open IDA. Select `Edit` -> `Plugins` -> `IDA-RPyC`. A windows would pop up:
   
   <img src="assets/pic0.png" width="400"/>

4. You can choose direct or SSL mode. Once parameters are set, you can click `Start` to start an RPyC server.

5. Now, at remote side, you can call IDA python APIs like this:

   ```py
   import rpyc

   conn = rpyc.connect('localhost', 54444, service = rpyc.MasterService)
   
   current_ea = conn.modules.idc.here()
   some_bytes = comm.modules.idaapi.get_bytes(current_ea, 4)
   print('0x{:x}: {}'.format(current_ea, some_bytes))
   ```

## 2. Screen recoding

![screen-recording.png](assets/screen-recording.gif)
