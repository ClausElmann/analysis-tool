# Architecture Guide

- This system uses vertical slice architecture.
- Each feature is self-contained.
- Dapper is used for all data access.
- SQL must always be explicit and stored in .sql files.
- No ORM or hidden query generation is allowed.
- Authentication is custom JWT-based.
- All logic must be visible and traceable.
