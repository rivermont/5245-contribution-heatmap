Generate an svg calendar heatmap - similar to GitHub and others' - from several sources of contribution data.

Usage:
- Supports contributions from eBird (checklists), Observation.org and iNaturalist (observations), GitHub (commits), and OpenStreetMap (changesets).
- Run main.py to generate the svg output, which can then be included in a webpage as an 'img' or 'object'.

Hovering over a date square displays a tooltip with the date and number of contributions.

Future Improvements:
- Interactive calendar (select sources to display)
- Run daily and upload to a server
- Add Mediawiki source option, for Wikipedia and others
- Reduce package dependencies
