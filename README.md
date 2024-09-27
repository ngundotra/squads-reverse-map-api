# Squads Reverse Map API

This API provides a reverse map for the squads by returning the multisig address & squads version for a given vault address.

Run it locally with:
```sh
DUNE_API_KEY=<your-dune-api-key> uv run flask --app hello run
```

### Docker

```sh
$ docker build -t squads-reverse . --secret id=DUNE_API_KEY,env=<your-dune-api-key>
$ docker run -p 8999:8000 squads-reverse
```
Now access at `http://localhost:8999/squad/<vault_address>` 
