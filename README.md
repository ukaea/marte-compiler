# MARTe Compiler

This repository provides a server application which will compile C++ make files.

It is expected to be used in tandem with other MARTe2 tools, such as [marte2_python](https://github.com/ukaea/MARTe2-python) to create marte2 configuration files but primarily it compliments the XMARTe GUI and is setup to communicate with the GUI, please see the GUI documentation for details on how to set this up.

The expected usage/user of this software is a application acting as a client user automating compilations remotely for use on machines not setup for compilations locally.

``The server requires docker to be installed as a pre-requisite and the user setting this up to have administrative rights when needed.``

# Installation

The steps to install or upgrade are:

``` bash
curl https://git.ccfe.ac.uk/marte21/public/marte-compiler/-/raw/master/install.sh?inline=false | sudo bash
```

The steps so far here is simply setting up the directory and the python virtual environment.

`` Note: This repo only support python3.7+ as it depends on uvicorn 0.18 for large header support. ``

## Contributing & Support

When you require support please open an issue, if you would like to make adjustments to behaviour, code or additions to features, please do so as an issue and merge request.

**Note: You must comply with our guidelines as per the below.**

[Repository Guidelines](./Guidelines.md)

## Support

For support on using this application you can refer to the documentation found here:

[User Documentation](http://marte21.gitpages.ccfe.ac.uk/public/marte-compiler)

**Note: It is expected that this repository is used by other developers automating the process through their own application development, using a REST API.**

**If you have found a bug or have a feature request then please submit an issue within this repository.**

If you need additional support feel free to contact our team:

- [Edward Jones](mailto:edward.jones1@ukaea.uk)
- [Adam Stephen](mailto:adam.stephen@ukaea.uk)
- [Hudson Baker](mailto:hudson.baker@ukaea.uk)

Additionally you can utilise the MARTe Discord community server:

[MARTe Discord Server](https://discord.gg/anSXWtnprW)

## License

This software repository is provided under the European Union Public Licence as it's rooted in the use of MARTe2. You can find further details on the license [here](https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12).