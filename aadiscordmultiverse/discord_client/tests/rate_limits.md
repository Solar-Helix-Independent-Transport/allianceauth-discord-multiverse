# Discord rate limits

The following table shows the rate limit as reported from the API for different routes.

method | limit | reset | rate / s | bucket
-- | -- | -- | -- | --
add_guild_member | 10 | 10,000 | 1 | self
create_guild_role | 250 | 180,000,000 | 0.001 | self
delete_guild_role | g | g | g | g
guild_member | 5 | 1,000 | 5 | self
guild_roles | g | g | g | g
add_guild_member_role | 10 | 10,000 | 1 | B1
remove_guild_member_role | 10 | 10,000 | 1 | B1
modify_guild_member | 10 | 10,000 | 1 | self
remove_guild_member | 5 | 1,000 | 5 | self
current_user | g | g | g | g

Legend:

- g: global rate limit. API does not provide any rate limit infos for those routes.

- reset: Values in milliseconds.

- bucket: "self" means the rate limit is only counted for that route, Bx means the same rate limit is counted for multiple routes.

- Data was collected on 2020-MAY-07 and is subject to change.
