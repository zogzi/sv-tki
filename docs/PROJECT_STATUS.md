# Project status

The repository is a development foundation. Passing automated tests does not establish editorial quality, a live Discord connection, a paid AI account or a running production host.

## Implemented and checked offline

- Holiday date rules, Easter, Mother's Day and year rollover.
- SQLite delivery records, same-day catch-up and recovery checks for uncertain sends.
- Error isolation, logging, server configuration and language preferences.
- Latvian/English authored content and year-specific editions.
- Name-day opt-in with a loadable dataset; the full dataset is not included.
- Optional compatible AI introductions, configurable endpoint/model, actual date/context, owner-editable brief and persistent successful-result cache.
- Docker build and non-root container smoke validation, including the configurable AI adapter and cache with a mocked provider. No live provider request was made.

## Editorial work owned by the user

The existing generated drafts have not been accepted as the final voice. The owner will revise them. Do not treat `CONTENT_REVIEW.md`, the sample edition or the editable AI brief as approved publication copy. No further rewrite of those posts is included in this documentation/infrastructure revision.

## Still required

| Work | Current state | Completion evidence |
| --- | --- | --- |
| Hosting comparison with current prices | Candidates documented; official-site access blocked by this environment's network policy | Read current official offers, compare VAT/IP/setup/renewal costs and persistent-process terms. |
| Production host | Not selected or provisioned | Owner chooses/pays for or obtains an eligible free VM; deployment survives a reboot. |
| Live Discord | No credentials supplied | Successful login, permission/command checks, real preview/button and a controlled scheduled post. |
| Final post content | Owner will write/revise | Content accepted by the owner and correctly rendered in Discord. |
| Future-year relevance | Not implemented | Trusted live source retrieval, date/relevance checks, citations, persisted bilingual edition and fallback tests. |
| Real AI provider | No credentials or paid calls | Chosen provider/model tested for Latvian quality, format, latency, billing and fallback. |
| Operational monitoring | Logs/healthcheck exist, external monitoring not configured | Notification on prolonged outage/unhealthy state, and a successful backup/restore drill. |

## Recommended order

1. Verify hosting offers and choose a persistent host; establish a small separate AI budget if AI is wanted.
2. Finish the owner's writing brief and a few representative posts, rather than rewriting the whole calendar before the voice is settled.
3. Implement one source-backed holiday end to end, including citations and persisted translations. Test it with a simulated future date and stale/missing sources.
4. Validate live in a private Discord test channel, then enable only reviewed content in production.

Network additions needed for official-site research were saved in the cloud configuration draft. Saving the draft does not itself apply network changes or provision hosting. Review/save the settings and publish when required by the environment UI.
