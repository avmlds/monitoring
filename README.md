# Universal Monitoring Tool

Universal tool to monitor statuses of multiple services over HTTP/S.
Service is able to poll required endpoints and send result to a remote PostgreSQL database.

## What's Inside:
The workflow is written using asyncio. When you launch the program, you actually launch two workers:
- `Agent` - responsible for making requests to specified HTTP endpoints. It utilizes a priority queue (python heapq) to schedule task execution. Task pool is limited to one coroutine.
- `Exporter` - takes care of exporting data to an external PostgreSQL. Connection to a remote database uses a connection pool with automatic reconnect. 
  After receiving SIGINT application will stop making requests and finish uploading all the requested data to the external database.

Tested with ~1000 remote endpoints.

## Limitations

- You can have multiple configuration files and use them for different services.
- If you add too many services you may start receiving error messages with a suggestion to increase the number of workers.
- If you want to use multiple app instances, make sure that you are not monitoring the same services in the same way from different apps.
  It will result in duplicates in the remote database.
- Respect the rate limits of services you monitor and never DDoS them.

## Example

- Make sure you have `Python 3.12+` installed, as well as `make` and `docker-compose`.
  - (`docker-compose` is required only for this tutorial)
- Don't forget to call `docker-compose down -v` and `make clean` after finishing this tutorial.
    The configuration file and local database won't be deleted. 
- Default config will be created at `~/.monitoring/monitoring-config`

```shell
git clone <repo>
cd <folder with repo>
make install
docker-compose up -d  # this will bootstrap a local postgres and an example application that you can monitor. 
# Look inside the docker-compose.yaml file for more details.
source .venv/bin/activate
export DATABASE_URI=postgresql://test:1234567890@127.0.0.1:5432/test
monitor config services add http://localhost:8000/ GET
monitor config services add http://localhost:8000/openapi.json GET --regex '\{"openapi":"3\.1\.0"' --check-regex
monitor config services show # lets look at our configuration
+------------------------------------+--------+-------------+-----------------------+--------------+---------+
|                url                 | method | check_regex |         regex         | interval_sec | timeout |
+------------------------------------+--------+-------------+-----------------------+--------------+---------+
|       http://localhost:8000/       |  GET   |    False    |          None         |      5       |    15   |
| http://localhost:8000/openapi.json |  GET   |     True    | \{"openapi":"3\.1\.0" |      5       |    15   |
+------------------------------------+--------+-------------+-----------------------+--------------+---------+


```
Before we start, lets look at all configuration options.
- `-v` Change the verbosity (logging) level in a convenient manner: `monitor start -v` `-->` `monitor start -vvvvv`
- `--export-batch-size` Size of one export in items. Valid value is an integer between 1 and 5000.
- `--export-interval` Interval in seconds between export routines. Valid value in an integer between 1 and 100.
- `-ns` Add systemd notification (You don't need it in most cases, but if you do, check the `http-monitoring.service` file).
- `--yes / -y` Start monitoring without a confirmation prompt. It is a must when starting with systemd.
- `--config-path` Path to the configuration file.


```shell
$ monitor start --help
Usage: monitor start [OPTIONS]

  Start monitoring.

Options:
  -v                           Logging level.
  --export-batch-size INTEGER  Size of one export in items.
  --export-interval INTEGER    Interval in seconds between export routines.
  -ns, --notify-systemd        Notify systemd after application start.
  -y, --yes                    Start without a confirmation prompt.
  --config-path PATH           Path to the configuration file.
  --help                       Show this message and exit.
```

Let's start:
```shell
$ monitor start -vvvv                                   

Are you sure want to start monitoring? Config path: /home/alexander/.monitoring/monitoring-config [y/N]: y

WARNING | 2024-06-10 18:33:51,295 | execution | 26 | Average requests per second (RPS) across all services: 0.20
WARNING | 2024-06-10 18:33:51,295 | execution | 27 | Total requests per second (RPS) across all services: 0.40
WARNING | 2024-06-10 18:33:51,295 | config | 110 | Systemd notification is disabled.
INFO | 2024-06-10 18:33:51,306 | utils | 42 | Success | 404 | 'GET' | 'http://localhost:8000/'
INFO | 2024-06-10 18:33:51,307 | utils | 42 | Success | 200 | 'GET' | 'http://localhost:8000/openapi.json'
INFO | 2024-06-10 18:33:51,314 | task_manager | 114 | Exported 1 elements.
INFO | 2024-06-10 18:33:53,326 | task_manager | 114 | Exported 1 elements.
INFO | 2024-06-10 18:33:55,330 | task_manager | 114 | Exported 0 elements.
INFO | 2024-06-10 18:33:56,313 | utils | 42 | Success | 404 | 'GET' | 'http://localhost:8000/'
INFO | 2024-06-10 18:33:56,317 | utils | 42 | Success | 200 | 'GET' | 'http://localhost:8000/openapi.json'

^C

WARNING | 2024-06-10 18:33:57,068 | execution | 74 | Killswitch engaged. Shutting down the application.
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
