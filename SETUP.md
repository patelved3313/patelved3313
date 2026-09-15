# Profile maintenance

The public README is the portfolio. This file documents how to maintain it.

## Content and artwork

- Keep project claims tied to the implementation in the linked repositories.
- Use “Seneca Polytechnic graduate” until a specific credential is confirmed.
- Use native Markdown for important prose, skills, and contact information.
- The hero and activity panel use `<picture>` with a mobile source below 600 px.
- Palette: graphite `#101210`, surface `#191D18`, off-white `#F1F3E8`, muted `#A8B09F`, lime `#D5FF70`, border `#343B31`.
- SVGs use Arial/Helvetica fallbacks, self-contained backgrounds, and no animation, scripts, or remote fonts.

## GitHub activity

`assets/activity.svg` and `assets/activity-mobile.svg` are checked-in snapshots of the public GitHub contribution calendar. They show the current daily streak, longest daily streak, and a graph of the last 31 days. Both include their refresh date.

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/update_activity.py
```

The script reads `github.com/users/patelved3313/contributions` for every calendar year since the account was created in January 2026. It uses the public calendar’s exact accessible counts, including any aggregate contributions GitHub chooses to display publicly. It never reads private repositories or needs a personal access token. Streaks count consecutive calendar dates with at least one contribution. An empty today preserves a streak ending yesterday; a missed yesterday resets it. The reference date and refresh timestamp use UTC. Longest streak spans all fetched years, including year boundaries.

The generator requires every expected date and a valid count, builds and XML-validates both images, then replaces the snapshots. A network failure or GitHub markup change fails the job before publishing new images; the last valid snapshots remain visible with their original dates. The public calendar’s HTML is an upstream dependency: if its accessible markup changes, update the parser. GitHub may revise contribution counts, and its image cache may delay display of a new snapshot.

### Automation after merge

The **Profile assets** workflow tests changes on pushes and pull requests. A separate refresh job runs daily at approximately 06:23 UTC and supports manual dispatch. It is restricted to the default branch and starts operating after merge; the redesign PR does not enable it on `main` in advance.

The refresh job commits only the two activity SVGs using the GitHub Actions bot and its built-in `GITHUB_TOKEN` with `contents: write`. No added secrets or third-party widget hosting are required. These bot commits are not attributed to Ved. If branch rules prohibit bot pushes, allow this workflow through the existing policy or run the generator on a branch and open an update PR. A failed push leaves the displayed snapshots unchanged.

GitHub may delay scheduled jobs or disable schedules in an inactive public repository after 60 days. The timestamp and direct contribution-history link make freshness visible. To pause automatic updates, disable the workflow in Actions; the last images remain usable.

## Verification before a profile PR

- Run the activity tests, refresh the images, and validate all SVG XML.
- Render the README through GitHub; check picture sources and every local asset.
- Inspect light and dark themes at desktop, medium, and phone widths.
- Recheck project/demo links and content accuracy.
- Review `git diff --check`, the complete diff, and staged files.
- Work on a branch and open a PR; do not merge it without the owner’s review.
