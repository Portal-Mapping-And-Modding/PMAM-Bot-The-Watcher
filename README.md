# Portal Mapping And Modding's Offical Discord Bot: The Watcher

The [discord.py](https://github.com/Rapptz/discord.py) bot used in the Portal Mapping And Modding Discord server named The Watcher.

***This bot is still a work in progress! Some bugs and other issues are expected to happen!***

- The `main` branch contains the code set the bot runs on the Discord server.
- The `stable` branch is a backup branch that contains the last stable code set for the bot. Used if `main` breaks.
- The `dev` branch is the bot's development and testing branch. Any new changes go through here before going into `main`.

**Setting Up The Bot:**

The Watcher uses the Python version `3.12.5`.

Simply use `pip install -r ./requirements.txt` to install all required python modules.

If using Linux, optionally the systemd python package can be installed for logging to be sent to journal.
The systemd header files are needed for this. If they are not installed, they can be installed using your distribution's package manager. Ex: `sudo apt install libsystemd-dev`. Once this is done then using `pip install systemd` will not result in the package failing to install and allowing you to access the bots logging with `journalctl` or `systemctl` when the bot is run as a service.

This bot uses the [`GNU Affero General Public License v3.0 (GNU AGPL V3.0)`](https://choosealicense.com/licenses/agpl-3.0/#) License.
