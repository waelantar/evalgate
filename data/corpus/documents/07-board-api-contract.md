# Northstar Board API Contract v1

## Purpose
The fictional Board API provides a bounded internal read model for current published status. It is not a general query interface and exposes no arbitrary event search.

## Authentication
Clients present a short-lived service credential issued by the fictional access process. Credentials are checked at the gateway; credentials and authorization headers are never stored in application logs.

## Status response
A successful status response includes source key, published state, event reference, event time, receipt time, and staleness flag. It does not include raw event notes or signatures.

## Unavailable response
If the ledger is unavailable or its migration state is not current, the API returns a typed unavailable response. It does not serve a cached status as though it were current.

## Bounds
The list operation returns at most 100 source summaries. A client must use documented pagination for the next page and cannot request an unrestricted export.

## Error semantics
Authentication failures, invalid source keys, unavailable ledger, and rate limits use distinct machine-readable codes. Error messages avoid revealing credentials or raw payloads.

## Caching
Clients may cache a successful response for no more than 15 seconds and must preserve its staleness flag. They must not extend the cache during an unavailable response.

## Non-goal
The Board API has no write endpoint. Field updates arrive only through the signed Relay Intake boundary.
