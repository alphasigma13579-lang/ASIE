# Module Card

## Identity

| Field | Value |
| --- | --- |
| Module ID |  |
| Module Name |  |
| Owner |  |
| Version |  |
| Classification |  |
| Affected AAS |  |

## Purpose

Define the capability this Module owns.

## Non-Goals

List what this Module must not do.

## Contracts

| Contract ID | Purpose | Direction |
| --- | --- | --- |
|  |  |  |

## Sockets

| Socket ID | Accepted Messages | Returned Messages |
| --- | --- | --- |
|  |  |  |

## Capabilities

- 

## Dependencies

- 

## Permissions

- 

## Lifecycle

```text
Install -> Register -> Validate -> Load -> Start -> Healthy -> Pause -> Resume -> Unload -> Remove
```

## Health

| Check | Passing Condition |
| --- | --- |
|  |  |

## Message Flow

```text
Source -> Socket Contract Layer -> APP -> ASIE System Bus -> Target Socket -> Module
```

## Zero Trust Notes

- 

## Acceptance Criteria

- No direct Module-to-Module communication.
- All interactions have Contract and Socket.
- All messages use APP where applicable.
- All permissions are least-privilege.

