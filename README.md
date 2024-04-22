# Universal Monitoring Tool

Universal tool to monitor statuses of multiple services over HTTP/S.
Stores intermediate results in a local SQLite database and then pushes them to a remote PostgreSQL database.

## What's Inside:
The workflow is written using asyncio. When you launch the program, you actually launch three workers:

- `Agent` - responsible for making requests to specified HTTP endpoints.
- `Exporter` - takes care of exporting dumped data to an external PostgreSQL.
- `Collector` - takes care of removing processed items from a local database.

`Agent` can function independently of `Exporter`, but your local database will start growing quite fast.
`Exporter` can operate without `Collector`, but your local database will start to grow quite fast,
and in such cases, it will mainly consist of processed items.
`Collector` also doesn't need other workers. It will keep your local database clean.

The tool uses SQLite as a local database to store records.
All three workers utilize the same connections to a local database.
Connection to a remote database uses a connection pool with automatic reconnect.

The system is more or less fault-tolerant; remote services can stop responding,
the remote database can become unavailable; nonetheless, monitoring won't stop working.

Tested with ~300 remote endpoints, ~3200 requests per minute.

## Limitations

- SQLite has perfect performance, but you must not launch two app instances targeting the same local database. 
  Concurrent read access is possible if you poke around WAL.
- You can have multiple configuration files and use them for different services. **Make sure they point to different local databases!**
- If you want to use multiple app instances, make sure that you are not monitoring the same services in the same way from different apps.
  It will result in duplicates in the remote database.
- Respect the rate limits of services you monitor and never DDoS them.

## Example

- Make sure you have `Python 3.7+` installed, as well as `make` and `docker-compose`.
  - (`docker-compose` is required only for this tutorial)
- Don't forget to call `docker-compose down -v` and `make clean` after finishing this tutorial.
    The configuration file and local database won't be deleted. 
- Default config will be created at `~/.monitoring/monitoring-config` 
- Default local database path is `~/.monitoring/local-database.sqlite3`

```shell
git clone <repo>
cd <folder with repo>
make install
docker-compose up -d  # this will bootstrap a local postgres and an example application that you can monitor. 
# Look inside the docker-compose.yaml file for more details.
source .venv/bin/activate
monitor config create postgresql://test:1234567890@127.0.0.1:5432/test
monitor config services add http://localhost:8000/ GET
monitor config services add http://localhost:8000/openapi.json GET --regex '\{"openapi":"3\.1\.0"' --check-regex
monitor config show # lets look at our configuration
+----------+----------------------------------------------------+
|   Name   |                       Value                        |
+----------+----------------------------------------------------+
|  Local   | ~/.monitoring/local-database.sqlite3 |
| External |  postgresql://test:1234567890@127.0.0.1:5432/test  |
+----------+----------------------------------------------------+
+------------------------------------+--------+-------------+-----------------------+--------------+---------+
|                url                 | method | check_regex |         regex         | interval_sec | timeout |
+------------------------------------+--------+-------------+-----------------------+--------------+---------+
|       http://localhost:8000/       |  GET   |    False    |          None         |      5       |    15   |
| http://localhost:8000/openapi.json |  GET   |     True    | \{"openapi":"3\.1\.0" |      5       |    15   |
+------------------------------------+--------+-------------+-----------------------+--------------+---------+


```
Before we start, lets look at all configuration options.
- `-v` Change the verbosity (logging) level in a convenient manner: `monitor start -v` `-->` `monitor start -vvvvv`
- `-ns` Add systemd notification (You don't need it in most cases, but if you do, check the `http-monitoring.service` file).
- `--yes` Start monitoring without a confirmation prompt. It is a must when starting with systemd.

```shell
$ monitor start --help
Usage: monitor start [OPTIONS]

  Start monitoring.

Options:
  -v                     Logging level.
  -ns, --notify-systemd  Notify systemd after application start.
  --yes                  Start without a confirmation prompt.
  --config-path PATH     Path to the configuration file.
  --help                 Show this message and exit.
```

Let's start:
```shell
$ monitor start -vvvv       
Are you sure want to start monitoring? Config path: ~/.monitoring/monitoring-config [y/N]: y

INFO | 2024-04-22 12:35:30,970 | config | 100 | Systemd notification is disabled.
INFO | 2024-04-22 12:35:30,970 | monitoring | 40 | Starting Agent worker.
INFO | 2024-04-22 12:35:30,970 | monitoring | 18 | Average requests per minute (RPM) across all services: 12.00
INFO | 2024-04-22 12:35:30,970 | monitoring | 19 | Total requests per minute (RPM) across all services: 24.00
INFO | 2024-04-22 12:35:30,970 | base | 33 | Starting Collector worker.
INFO | 2024-04-22 12:35:30,971 | base | 33 | Starting Exporter worker.
INFO | 2024-04-22 12:35:30,983 | export | 70 | No records to export.
INFO | 2024-04-22 12:35:32,012 | export | 63 | Exported 2 records.
INFO | 2024-04-22 12:35:32,993 | cleanup | 23 | 2 processed records deleted.
INFO | 2024-04-22 12:35:33,013 | export | 70 | No records to export.
```

To delete or update a service you have look at it first and obtain a service number.
```shell
monitor config services show --numbered

+---+------------------------------------+--------+-------------+-----------------------+--------------+---------+
| № |                url                 | method | check_regex |         regex         | interval_sec | timeout |
+---+------------------------------------+--------+-------------+-----------------------+--------------+---------+
| 0 |       http://localhost:8000/       |  GET   |    False    |          None         |      5       |    15   |
| 1 | http://localhost:8000/openapi.json |  GET   |     True    | \{"openapi":"3\.1\.0" |      5       |    15   |
+---+------------------------------------+--------+-------------+-----------------------+--------------+---------+
```
After you know the number, you can update it
```shell
monitor config services update --help

Usage: monitor config services update [OPTIONS] NUMBER

  Update service under NUMBER in the configuration.

  To get a number, run `monitor config services show --numbered`

Options:
  --toggle-check-regex  Toggle regex checking mode.
  --regex TEXT          Regexp to check.
  --timeout INTEGER     Timeout for outgoing connections to a service.
  --interval INTEGER    Interval in seconds between requests. Must be between
                        5 and 300.
  --config-path PATH    Path to the configuration file.
  --help                Show this message and exit.
````
Or delete a service
```shell
monitor config services remove --help
Usage: monitor config services remove [OPTIONS] NUMBER

  Remove a service under NUMBER in the configuration.

  To get a number, run `monitor config services show --numbered`

Options:
  --config-path PATH  Path to the configuration file.
  --help              Show this message and exit.
```
