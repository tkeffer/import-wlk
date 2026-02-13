# WLK importer

This extension imports WLK files into WeeWX by emulating a driver. This has the
advantage of subjecting the imported data to the same processing pipeline as
real data, including any extensions.

## Prerequisites

- Python 3.7+
- WeeWX V4.6+

## Installing the extension

### Copy your configuration file

This extension requires modifying your `weewx.conf` file. Rather tha modify your
only copy of the file, it's safer to make a copy, then use that.

```shell
cp ~/weewx-data/weewx.conf /var/tmp/weewx.conf
```

### Run the installer

The extension is installed like any other WeeWX extension, except that you
should use the config file created above:

```shell
weectl extension --config=/var/tmp/weewx.conf install https://github.com/tkeffer/weewx-wlk/archive/refs/heads/master.zip 
```

### Configure the extension

1. Stop `weewxd`.

2. Edit the copy of `weewx.conf` to set the driver to the WLK importer. Under the
`[Station]` stanza, change the line `station_type` so it reads:

       station_type = WLK

3. In the `[WLK]` stanza, set option `wlk_files` to the pathway to the WLK
   file(s) that you intend to import. Wildcards can be used. The tilde symbol
   (`~`) can also be used. For example:

    ```
   [WLK]
        wlk_files = ~/Downloads/2018-??.wlk
   ```

   In this example, all WLK files with 2018 dates would be imported.  Substitute
   as necessary.

4. Run `weewxd` [directly from the command line](https://www.weewx.com/docs/5.2/usersguide/running/#running-directly),
   using the config file that you created. Typically, this looks like:

       weewxd --config=/var/tmp/weewx.conf

   Monitor the output to make sure that the import is successful. When the import
   is complete, it will end with a not-implemented error that looks like this:

       NotImplementedError: WLK import complete. Ignore this exception.

   This is the normal end of the import process.
    
5. Restart `weewxd`. 

## Licensing

WeeWX is licensed under the GNU Public License v3.

## Copyright

© 2009-2026 Thomas Keffer, Matthew Wall, and Gary Roderick
