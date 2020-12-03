# YouTubeEditor (aka YouTuberizer)

YouTuberizer is a Sublime Text package for working with and managing your
YouTube channel from directly within Sublime Text itself. It started as a small
sub-project for Devember 2019, and is the main focus of Devember 2020.

If you're reading this during December 2020, you can view daily updates on
progress as well as live streams on my [Live Stream Channel on
YouTube](https://www.youtube.com/c/TerenceMartinLive).

If you'd like to play with the code, you will also need the [googleapiclient
super dependency](https://github.com/OdatNurd/googleapiclient) installed as
well. Clone that repository into your `Packages` folder and select `Package
Control: Install Local Dependency` to install the dependency. Once the
dependency is in place, you can install the package.

*NOTE* Although this package runs in the Python 3.3 plugin host, a build of
Sublime Text >= 4082 is required, as the package uses some of the new API's
available only in those builds.

Additionally, in order to use this package, you need to set yourself up with
YouTube API access from the google developer console. Once your app is set up,
edit the YouTubeEditor settings and include the required keys in your custom
configuration.

