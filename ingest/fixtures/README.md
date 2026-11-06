# Test snapshot

`2026-2027/` is a frozen subset (~200 courses) of the ExploreCourses catalog, in the same layout `make fetch`
produces: one gzipped XML file per department. Tests and local development use it instead of the live site.

Courses were picked by `ingest/make_fixture.py` to cover every data quirk in the full catalog (by-arrangement
sections, time-TBA classes, cross-listings, partial-quarter dates, weekend meetings, messy WAYS tags, odd
units, …), plus a few well-known anchor courses and ordinary ones. `manifest.json` lists each course and why
it was picked. Cross-listing groups are always kept whole.

Rebuild after a fresh download (this changes test data, so review the diff):

```sh
make fetch
make fixture
```
