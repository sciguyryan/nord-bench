# NordVPN server benchmarker

A small Python utility for finding NordVPN OpenVPN endpoints with promising network latency. It can read an existing directory of `.ovpn` files or download NordVPN's official configuration archive, then measure the destinations concurrently and print a ranked terminal table.

The distinction between a responsive IP address and a good VPN server matters here. This prototype uses ICMP echo requests, not an OpenVPN tunnel. A low ping time does not establish that the VPN service is available or that its throughput will be good. Servers that do not respond to ICMP are not necessarily offline.

## Requirements

Python 3.10 or later and the system `ping` executable. No third-party Python packages are required. The prototype is developed for Linux, with Windows and macOS command variants provided but not yet tested on those platforms.

## Quick start

To download NordVPN's [official OpenVPN configuration archive](https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip), extract it temporarily and benchmark UDP endpoints:

```bash
python nordvpn_benchmark.py --download --accuracy balanced --top 10
```

To use files already on disk:

```bash
python nordvpn_benchmark.py --config-dir ~/nordvpn --protocol both --accuracy thorough --top 20
```

To save the complete result set, including preliminary measurements and failures:

```bash
python nordvpn_benchmark.py --download --output results.csv --format csv
```

JSON and plain-text tables are also available with `--format json` and `--format table`. File export is optional. The `--top` option limits only the displayed table, not the exported records.

## Command-line options

| Option | Purpose |
| --- | --- |
| `--config-dir PATH` | Recursively discover local `.ovpn` files. |
| `--download` | Download and temporarily extract the official archive. |
| `--protocol udp\|tcp\|both` | Filter configuration transport; defaults to UDP. |
| `--accuracy fast\|balanced\|thorough` | Choose the measurement depth; defaults to balanced. |
| `--top N` | Display the first N ranked endpoint records; defaults to 10. |
| `--workers N` | Maximum concurrent ping subprocesses; defaults to 24. |
| `--timeout SECONDS` | Per-request timeout used for ping; defaults to 1. |
| `--output FILE` | Optionally write all results to a file. |
| `--format csv\|json\|table` | Export format; defaults to CSV. |
| `--ascii` | Use ASCII rather than Unicode table borders. |
| `--colourblind`, `--colorblind` | Use the alternative blue-to-orange latency palette. |
| `--no-colour`, `--no-color` | Disable terminal colour. |
| `--quiet` | Suppress progress messages. |
| `--verbose` | Report malformed or unsupported configurations. |

The two input options are mutually exclusive. Run `python nordvpn_benchmark.py --help` for the current CLI.

## Measurements and ranking

The initial survey sends 2, 3 or 5 ICMP requests per unique destination for fast, balanced and thorough modes respectively. A shortlist then receives 6, 12 or 25 additional requests. Survey measurements are retained. The shortlist is at least 20 destinations or three times the requested top count, whichever is larger, capped at the number discovered. These are provisional heuristics, not empirically optimised defaults.

A result records successful reply times, attempted and received probes, loss percentage, median latency and median absolute deviation (MAD) from the median. The ordering prefers lower packet loss, then lower median latency, then lower MAD. This deliberately favours reliability, although packet loss estimated from a handful of requests is uncertain. Survey-only results remain marked as such, so they are not mistaken for fully refined measurements.

ICMP probes are deduplicated by destination address, not by configuration filename or port. Multiple OpenVPN profiles using the same destination can therefore share a measurement. This is correct for ICMP but says nothing about whether their individual VPN ports work.

## Filtering configurations

Use `--filter EXPR` to select endpoints before probing. The language supports `!` (NOT), `&` (AND), `|` (OR), and parentheses, with precedence in that order. A bare two-letter code means `country:CODE`; a server identifier such as `uk2108` means `server:uk2108`. Named fields are `country`, `server`, `host`, `protocol`, and `port`. The `server` and `host` fields support `*` wildcards. Filters are case-insensitive, and repeated `--filter` options are combined using AND.

To exclude both UK and US servers:

```bash
python nordvpn_benchmark.py --download --filter='!(uk|us)'
```

To benchmark only UK or Netherlands UDP endpoints, excluding one server:

```bash
python nordvpn_benchmark.py --download --filter='(uk|nl)&protocol:udp&!server:uk2108'
```

The expression `!uk|!us` does **not** exclude both countries: by ordinary Boolean OR semantics, it matches both UK and US servers. Use `!(uk|us)` or `!uk&!us` instead. Quote expressions in the shell because `|`, `&`, `!`, and parentheses may have special meaning.

Filters are applied after configuration parsing and before any network probes. Download mode currently extracts the selected transport profiles before applying expression filters; this reduces probing work but does not yet reduce extraction work for country or server filters. Invalid expressions fail before downloading or probing. If no endpoints match, the program reports the empty selection rather than probing anything.

The table shows canonical server hostnames such as `uk2108.nordvpn.com`, not archive filenames such as `09150-uk2108.nordvpn.com.udp_2.6.ovpn`. CSV and JSON exports retain the original configuration filename as `config_file` for traceability. Auto-connect uses the same canonical identity.

## Latency colours

The terminal table includes mean and median ICMP latency. Mean values use a continuous green-to-red colour scale by default, with fixed reference points from 0 to 250 ms. A fixed scale matters because a relatively quick server in a slow batch should not automatically appear green. The alternative `--colourblind` or `--colorblind` option uses a blue-to-orange palette. It is intended to be easier to distinguish for some forms of colour-vision deficiency, although no palette is universally accessible.

Colours are presentation only. Ranking still uses packet loss, median latency and MAD, and the numeric values remain visible without colour. ANSI true-colour sequences are emitted only when stdout is an interactive terminal that supports conventional terminal controls; `NO_COLOR`, `TERM=dumb`, `--no-colour` and `--no-color` disable them. `--ascii` affects table borders independently. Exported files never contain ANSI colour sequences. Some terminals may render true colour differently or not at all.

## Progress and output

During each stage, stderr shows completed addresses, responding addresses, elapsed time and an approximate ETA. Interactive terminals refresh a single status line; redirected output receives periodic status lines. Standard output contains the final table. `--quiet` suppresses routine progress, not the final table.

The CSV export includes endpoint identity, transport, port, stage, probe counts, loss, median mean and median latency, MAD and error text. JSON additionally includes the raw successful reply times. The table export is a human-readable summary, not a lossless sample record.

## Automatic downloads

`--download` streams the archive over HTTPS, filters for the selected transport before applying bounded extraction limits, extracts `.ovpn` files into a temporary directory and removes the temporary files when the run finishes. It does not cache downloads. It also does not require or read VPN credentials. The download may be substantially larger than the files needed for a single protocol.

## Limitations and next steps

This is an initial prototype. It has not yet been calibrated against real NordVPN endpoints, and the current ping output parser is primarily aimed at conventional English-language `ping` output. The Linux implementation uses one `ping` process per destination per stage, which is simple and bounded but not necessarily the fastest possible probing strategy. Progress estimates are approximate, and pressing Ctrl+C during a batch does not yet produce a partial export.

Potential follow-up work includes empirical concurrency tuning, better handling of unresponsive survey candidates, cross-platform ping validation, a more efficient probe engine and optional genuine OpenVPN endpoint validation. None of those should be presented as implemented until tested.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Connecting to a ranked server on Linux

The optional `--auto-connect` flag asks the installed NordVPN Linux CLI to connect to the first ranked server after the benchmark. It is not the NordVPN client's persistent auto-connect setting. `--connect-rank N` chooses a different rank among the displayed top results. For example:

```bash
python nordvpn_benchmark.py --download --top 20 --auto-connect --connect-rank 2
```

The benchmarker checks for `nordvpn`, reads its connection status, and derives a server identifier from the canonical server hostname. It will not attempt a connection when that identifier is unavailable or the selected server returned no ICMP responses. An existing connection is left alone unless you confirm replacement interactively, or supply `--replace-connection` explicitly. Non-interactive runs cannot prompt, so they require that flag to replace an existing connection.

After issuing `nordvpn connect SERVER`, the script checks `nordvpn status` and requires the reported server to match the requested server. A failed connection returns a non-zero exit status without discarding an export already written. The client must already be installed, configured and logged in. No credentials are handled by this script, and it does not change NordVPN's configured VPN technology. Consequently, the resulting VPN transport may differ from the OpenVPN profile used for ICMP discovery. The client may also refuse a server identifier that is no longer available.

The status parser currently recognises English `Status:` and `Current server:` output. Other client versions and localisations need testing; an unrecognised response causes the connection operation to stop rather than guessing. Actual client integration has not yet been verified on a live NordVPN session.

## Continuous integration and formatting

GitHub Actions runs the unit tests and checks Python source formatting on pushes and pull requests. Ruff is pinned to version 0.14.2 for consistent CI behaviour. To apply its formatting locally before committing, run:

```bash
python -m pip install 'ruff==0.14.2'
ruff format .
ruff format --check --diff .
python -m unittest discover -s tests -v
```

The CI formatting check is deliberately read-only and fails if source files need formatting. It does not automatically rewrite committed code.

## Country names and named region lists

The Country column is derived from NordVPN's server identifier. Country names come from the bundled `country_names.json` snapshot, generated from `pycountry`'s ISO 3166 data during development. The runtime does not need `pycountry` or a geolocation service. NordVPN's `uk` prefix is mapped to the United Kingdom; the prefix represents NordVPN's advertised location, not independent evidence of physical server placement.

The bundled `region-lists.json` provides a curated, experimental `low-ads` group containing Andorra (`ad`), Albania (`al`), the Bahamas (`bs`), Belize (`bz`), Monaco (`mc`), Papua New Guinea (`pg`), Trinidad and Tobago (`tt`) and Uzbekistan (`uz`). These locations were selected from NordVPN’s advertised server countries with reference to YouTube’s published monetised-market list. This is a practical shortlist for testing whether YouTube serves fewer adverts, not a general advertising classification, an ad blocker or a guarantee. The list is maintained for NordVPN specifically. An advertised NordVPN location does not necessarily have a usable OpenVPN profile in the current archive, and actual advertising behaviour can change.

Sources for maintaining this curated list: https://nordvpn.com/servers/ and https://support.google.com/youtube/answer/1342206. Review both when updating the list; do not add countries solely because another VPN provider offers them.

```bash
python nordvpn_benchmark.py --download --region-list low-ads
python nordvpn_benchmark.py --download --filter='list:low-ads|country:nl'
python nordvpn_benchmark.py --list-region-lists
python nordvpn_benchmark.py --download --region-lists-file ~/.config/nordvpn-benchmark/regions.json --region-list low-ads
```

Custom JSON files have the same shape as the bundled catalogue: an object mapping group names to objects with a `description` string and a `countries` array of lowercase two-letter codes. Custom groups override built-in groups of the same name rather than merging them. Invalid codes, duplicate countries and malformed definitions are rejected before probing. Multiple `--region-list` options are combined using AND, like repeated `--filter` options.

## Distinct-server results

The terminal table displays one rank per canonical hostname and destination IP, rather than repeating the same ICMP measurement for each OpenVPN port. Where a hostname resolves to different measured IP addresses, those endpoints remain distinct. `--top` and `--connect-rank` refer to the displayed ranking. CSV and JSON exports continue to include every configuration and port, since ICMP does not test whether a particular OpenVPN port is available.

## Development checks

The GitHub Actions workflow runs the unit tests, `ruff check .` and `ruff format --check --diff .`, with Ruff pinned to version 0.14.2. Run the same commands locally before committing; the entry-point script must retain its executable bit in Git.

### Country-code aliases and ISO data

NordVPN server hostnames are preserved exactly, but country matching uses canonical ISO 3166-1 alpha-2 codes. For example, NordVPN's `uk` prefix maps to `gb`. Both `--filter uk` and `--filter gb` match UK servers; `country:uk` and `country:gb` are equivalent. Named region lists accept either spelling and normalise entries when loaded. Duplicate aliases such as `uk` and `gb` in the same list are rejected.

The country-name snapshot is generated, not hand-maintained. To update it, install the development-only dependency `pycountry==24.6.1` and run `python tools/generate_country_names.py`. CI checks the snapshot with `python tools/generate_country_names.py --check`. The runtime requires neither `pycountry` nor an internet connection for names. Provider-specific aliases remain deliberately explicit in `nordvpn_regions.py`. The curated `low-ads` list remains hand-maintained because ISO country data cannot establish advertising behaviour or NordVPN OpenVPN availability.

## Early country filtering

Country-only restrictions, including named region lists and Boolean expressions composed entirely of country and list selectors, are evaluated against recognised NordVPN configuration filenames before extraction and profile parsing. This reduces disk I/O and parsing work when a small subset of locations is selected. The full filter expression is still evaluated against parsed endpoints before DNS or ICMP measurements.

Filters that depend on server, host, transport or port metadata are evaluated after parsing. Mixed expressions are not used to exclude profiles early, because doing so could change the result of an OR expression. Filenames that do not match NordVPN's recognised naming convention also fall back to normal parsing. Country aliases such as `uk` and `gb` remain equivalent.

The OpenVPN ZIP is still downloaded in full; this optimisation does not reduce archive download bandwidth. It also does not change the ranking or export format.
