# WLK importer

This extension can import WLK files into WeeWX. It works by emulating a driver.
This has the advantage of subjecting the imported data to the same processing
pipeline as real data, including any extensions.

## Prerequisites

- Python 3.7+
- WeeWX V4.6+

## Installing the extension

### Run the installer

The extension is installed like any other WeeWX extension:

```shell
weectl extension install https://github.com/tkeffer/weewx-wlk/archive/refs/heads/master.zip 
```

### Configure the extension

1. Stop `weewxd`.

2. Edit `weewx.conf` to temporaily set the driver to the importer. Under the
`[Station]` stanza, change the line `station_type` so it reads:

       station_type = WLK

3. In the `[WLK]` stanza, set option `wlk_files` to the pathway to the WLK file(s) that you intend to
import. Wildcards can be used. The tilde symbol (`~`) can be used. For example:

    ```
   [WLK]
        wlk_files = ~/Downloads/2018-??.wlk
   ```

   In this example, all WLK files with 2018 dates would be imported.  Substitute
   the actual pathway.

4. Run `weewxd` [directly from the command line](https://www.weewx.com/docs/5.2/usersguide/running/#running-directly).
This allows you to monitor the files as they get imported.

5. When finished, be sure to set `station_type` back to its original setting. 

## Licensing

WeeWX is licensed under the GNU Public License v3.

## Copyright

© 2009-2026 Thomas Keffer, Matthew Wall, and Gary Roderick
