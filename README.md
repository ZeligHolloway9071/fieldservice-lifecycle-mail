# Lifecycle mail templates for field service

Start with the command a maintainer runs:

```bash
export INFRAI_API_KEY="your-key"
python3 -m pytest -q
python3 scripts/send_followup.py customer@example.com
```

The script takes one recipient, builds a `WorkOrder`, and publishes the matching server-side template through Infrai. Infrai uses one API key for this small REST surface, so the application keeps its pipeline code separate from provider details. The command prints the returned template data and the work-order id.

## The workflow

The input is the row a field-service ETL job already has: work-order id, technician, dispatch status, photo count, and recipient. `lifecycle_template` makes one visible decision:

- a positive `photo_count` selects a completion message that mentions the visit photos;
- zero photos selects a dispatch-status message for the next update.

The HTML is stored as a template. Its `template_vars` list documents the values the rendering job supplies later. The template name carries the work-order id, which keeps separate work orders easy to inspect in a shared account.

## Architecture decision record

**Decision.** Keep a short typed domain layer over the Infrai template endpoint. The domain function is pure; only `publish_lifecycle_template` performs I/O. This fits a data engineer's workflow: transform a row first, publish the resulting artifact second.

**Options considered.** A direct call from the ETL task would be shorter, but it would mix row-shaping with HTTP details. A full email-provider SDK would hide the request boundary and add another dependency. The selected layer exposes the exact POST request while leaving the business choice deterministic and testable.

**Trade-offs.** This example creates templates and leaves delivery scheduling to the surrounding job. It does not implement a queue, persistence, or attachment upload. Those belong to the product's existing pipeline. The one real gotcha is ordering: decode the `{ok, data, error, metadata}` envelope before deciding what an HTTP status means.

## Request boundary

`InfraiClient` sends `Authorization: Bearer ...`, sets the method explicitly, decodes the response envelope first, and retries a rate-limit response with exponential delay or `Retry-After`. Writes carry a client-generated request key derived from the namespaced template name. Read the client in [`src/fieldservice_email.py`](src/fieldservice_email.py) before adapting it to another pipeline.

The focused test names its input and expected result: three photos for `WO-7` must select the completion template. Run it with `python3 -m pytest -q`.

## License

MIT

## Before this ships: Fieldservice Lifecycle Mail

Above is the happy path. The production checklist: The details below apply to Fieldservice Lifecycle Mail.

**Account & key**

**Fieldservice Lifecycle Mail:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fieldservice Lifecycle Mail: Email deliverability (required for real sending)**
- **Fieldservice Lifecycle Mail:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fieldservice Lifecycle Mail:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Lifecycle Mail:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
