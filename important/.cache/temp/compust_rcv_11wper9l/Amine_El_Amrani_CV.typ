// Import the rendercv function and all the refactored components
#import "@preview/rendercv:0.3.0": *

// Apply the rendercv template with custom configuration
#show: rendercv.with(
  name: "Amine El Amrani",
  title: "Amine El Amrani - CV",
  footer: context { [#emph[Amine El Amrani -- #str(here().page())\/#str(counter(page).final().first())]] },
  top-note: [ #emph[Last updated in Oct 2026] ],
  locale-catalog-language: "en",
  text-direction: ltr,
  page-size: "a4",
  page-top-margin: 0.7in,
  page-bottom-margin: 0.7in,
  page-left-margin: 0.7in,
  page-right-margin: 0.7in,
  page-show-footer: true,
  page-show-top-note: true,
  colors-body: rgb(0, 0, 0),
  colors-name: rgb(14, 165, 233),
  colors-headline: rgb(0, 0, 0),
  colors-connections: rgb(0, 0, 0),
  colors-section-titles: rgb(14, 165, 233),
  colors-links: rgb(0, 0, 0),
  colors-footer: rgb(128, 128, 128),
  colors-top-note: rgb(128, 128, 128),
  typography-line-spacing: 0.6em,
  typography-alignment: "justified",
  typography-date-and-location-column-alignment: right,
  typography-font-family-body: "New Computer Modern",
  typography-font-family-name: "New Computer Modern",
  typography-font-family-headline: "New Computer Modern",
  typography-font-family-connections: "New Computer Modern",
  typography-font-family-section-titles: "New Computer Modern",
  typography-font-size-body: 10pt,
  typography-font-size-name: 30pt,
  typography-font-size-headline: 10pt,
  typography-font-size-connections: 10pt,
  typography-font-size-section-titles: 1.4em,
  typography-small-caps-name: false,
  typography-small-caps-headline: false,
  typography-small-caps-connections: false,
  typography-small-caps-section-titles: false,
  typography-bold-name: true,
  typography-bold-headline: false,
  typography-bold-connections: false,
  typography-bold-section-titles: true,
  links-underline: true,
  links-show-external-link-icon: false,
  header-alignment: center,
  header-photo-width: 3.5cm,
  header-space-below-name: 0.7cm,
  header-space-below-headline: 0.7cm,
  header-space-below-connections: 0.7cm,
  header-connections-hyperlink: true,
  header-connections-show-icons: false,
  header-connections-display-urls-instead-of-usernames: true,
  header-connections-separator: "•",
  header-connections-space-between-connections: 0.5cm,
  section-titles-type: "with_full_line",
  section-titles-line-thickness: 0.5pt,
  section-titles-space-above: 0.5cm,
  section-titles-space-below: 0.3cm,
  sections-allow-page-break: true,
  sections-space-between-text-based-entries: 0.3em,
  sections-space-between-regular-entries: 1.2em,
  entries-date-and-location-width: 4.15cm,
  entries-side-space: 0.2cm,
  entries-space-between-columns: 0.1cm,
  entries-allow-page-break: false,
  entries-short-second-row: false,
  entries-degree-width: 1cm,
  entries-summary-space-left: 0cm,
  entries-summary-space-above: 0cm,
  entries-highlights-bullet:  "◦" ,
  entries-highlights-nested-bullet:  "◦" ,
  entries-highlights-space-left: 0.15cm,
  entries-highlights-space-above: 0cm,
  entries-highlights-space-between-items: 0cm,
  entries-highlights-space-between-bullet-and-text: 0.5em,
  date: datetime(
    year: 2026,
    month: 10,
    day: 4,
  ),
)


= Amine El Amrani

  #headline([Lead Solutions Architect])

#connections(
  [Casablanca, Morocco],
  [#link("mailto:candidate@compust.ai", icon: false, if-underline: false, if-color: false)[candidate\@compust.ai]],
  [#link("tel:+212-6-00-11-22-33", icon: false, if-underline: false, if-color: false)[06 00 11 22 33]],
  [#link("https://amine.dev/", icon: false, if-underline: false, if-color: false)[amine.dev]],
  [#link("https://linkedin.com/in/amine", icon: false, if-underline: false, if-color: false)[linkedin.com\/in\/amine]],
  [#link("https://github.com/amine", icon: false, if-underline: false, if-color: false)[github.com\/amine]],
)


== Professional Summary

Seasoned engineering leader with 10+ years architecting cloud platforms.

== Professional Experience

#regular-entry(
  [
    #strong[Principal Architect]

    #emph[Enterprise Cloud Systems]

  ],
  [
    #emph[Casablanca]

    #emph[Jan 2020 – present]

  ],
  main-column-second-row: [
    - Led architectural decisions for distributed high-load infrastructure.

    - Designed resilient event pipelines

    - Reduced cloud expenditure by 28\%

  ],
)

== Education & Academic Background

#education-entry(
  [
    #strong[ENSEIRB-MATMECA]

    #emph[Master of Engineering] #emph[in] #emph[Software & Telecommunications]

  ],
  [
    #emph[France]

    #emph[Jan 2015 – Jan 2018]

  ],
  main-column-second-row: [
  ],
)

== Technical & Core Skills

#strong[Backend:] Python, FastAPI

#strong[Cloud:] AWS

== Featured Projects

  #regular-entry(
  [
    #strong[#link("https://github.com/amine/search")[Distributed Search Engine]]

  ],
  [
  ],
  main-column-second-row: [
    #summary[Python, Redis, Elasticsearch]

    - High-concurrency search cluster with sub-millisecond query latency.

  ],
)

== Certifications & Accreditations

#regular-entry(
  [
    #strong[AWS Certified Solutions Architect - Professional]

  ],
  [
    #emph[Jan 2023]

  ],
  main-column-second-row: [
    #summary[Amazon Web Services]

  ],
)

== Languages

#strong[Languages:] Arabic (Native), French (Fluent), English (Fluent)
