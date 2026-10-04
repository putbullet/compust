// Import the rendercv function and all the refactored components
#import "@preview/rendercv:0.3.0": *

// Apply the rendercv template with custom configuration
#show: rendercv.with(
  name: "Dr. Alexander von Humboldt",
  title: "Dr. Alexander von Humboldt - CV",
  footer: context { [#emph[Dr. Alexander von Humboldt -- #str(here().page())\/#str(counter(page).final().first())]] },
  top-note: [ #emph[Zuletzt aktualisiert Okt 2026] ],
  locale-catalog-language: "de",
  text-direction: ltr,
  page-size: "a4",
  page-top-margin: 0.7in,
  page-bottom-margin: 0.7in,
  page-left-margin: 0.7in,
  page-right-margin: 0.7in,
  page-show-footer: true,
  page-show-top-note: true,
  colors-body: rgb(0, 0, 0),
  colors-name: rgb(5, 150, 105),
  colors-headline: rgb(0, 79, 144),
  colors-connections: rgb(0, 79, 144),
  colors-section-titles: rgb(5, 150, 105),
  colors-links: rgb(0, 79, 144),
  colors-footer: rgb(128, 128, 128),
  colors-top-note: rgb(128, 128, 128),
  typography-line-spacing: 0.6em,
  typography-alignment: "justified",
  typography-date-and-location-column-alignment: right,
  typography-font-family-body: "Source Sans 3",
  typography-font-family-name: "Source Sans 3",
  typography-font-family-headline: "Source Sans 3",
  typography-font-family-connections: "Source Sans 3",
  typography-font-family-section-titles: "Source Sans 3",
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
  links-underline: false,
  links-show-external-link-icon: false,
  header-alignment: center,
  header-photo-width: 3.5cm,
  header-space-below-name: 0.7cm,
  header-space-below-headline: 0.7cm,
  header-space-below-connections: 0.7cm,
  header-connections-hyperlink: true,
  header-connections-show-icons: true,
  header-connections-display-urls-instead-of-usernames: false,
  header-connections-separator: "",
  header-connections-space-between-connections: 0.5cm,
  section-titles-type: "with_partial_line",
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
  entries-short-second-row: true,
  entries-degree-width: 1cm,
  entries-summary-space-left: 0cm,
  entries-summary-space-above: 0cm,
  entries-highlights-bullet:  "•" ,
  entries-highlights-nested-bullet:  "•" ,
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


= Dr. Alexander von Humboldt

  #headline([Distinguished Research Scientist & Distributed Systems Architect])

#connections(
  [#connection-with-icon("location-dot")[Berlin, Germany]],
  [#link("mailto:alexander.humboldt@university.de", icon: false, if-underline: false, if-color: false)[#connection-with-icon("envelope")[alexander.humboldt\@university.de]]],
  [#link("tel:+49-30-1234567", icon: false, if-underline: false, if-color: false)[#connection-with-icon("phone")[030 1234567]]],
)


== Kurzprofil

Pioneering researcher and systems engineer with over 15 years of experience leading high-performance computing initiatives across European research networks.

== Berufserfahrung

#regular-entry(
  [
    #strong[Research Lab Europe 1], Principal Systems Architect 1

    - Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.

    - Optimized memory bus saturation reducing compute cycle bottlenecks by 31\%.

    - Implemented lock-free asynchronous queue topologies handling 40M events\/sec.

    - Co-authored patent on distributed zero-copy network buffer management.

  ],
  [
    Berlin \/ Munich

    Jan 2011 – Dez 2012

  ],
)

#regular-entry(
  [
    #strong[Research Lab Europe 2], Principal Systems Architect 2

    - Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.

    - Optimized memory bus saturation reducing compute cycle bottlenecks by 32\%.

    - Implemented lock-free asynchronous queue topologies handling 40M events\/sec.

    - Co-authored patent on distributed zero-copy network buffer management.

  ],
  [
    Berlin \/ Munich

    Jan 2012 – Dez 2013

  ],
)

#regular-entry(
  [
    #strong[Research Lab Europe 3], Principal Systems Architect 3

    - Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.

    - Optimized memory bus saturation reducing compute cycle bottlenecks by 33\%.

    - Implemented lock-free asynchronous queue topologies handling 40M events\/sec.

    - Co-authored patent on distributed zero-copy network buffer management.

  ],
  [
    Berlin \/ Munich

    Jan 2013 – Dez 2014

  ],
)

#regular-entry(
  [
    #strong[Research Lab Europe 4], Principal Systems Architect 4

    - Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.

    - Optimized memory bus saturation reducing compute cycle bottlenecks by 34\%.

    - Implemented lock-free asynchronous queue topologies handling 40M events\/sec.

    - Co-authored patent on distributed zero-copy network buffer management.

  ],
  [
    Berlin \/ Munich

    Jan 2014 – Dez 2015

  ],
)

#regular-entry(
  [
    #strong[Research Lab Europe 5], Principal Systems Architect 5

    - Architected high-throughput parallel compute cluster for astronomical data analysis across tier-1 data centers.

    - Optimized memory bus saturation reducing compute cycle bottlenecks by 35\%.

    - Implemented lock-free asynchronous queue topologies handling 40M events\/sec.

    - Co-authored patent on distributed zero-copy network buffer management.

  ],
  [
    Berlin \/ Munich

    Jan 2015 – Dez 2016

  ],
)

== Ausbildung

#education-entry(
  [
    #strong[Technical University of Berlin 1], Computer Science & Parallel Architectures

    - GPA \/ Honors: Summa Cum Laude

    - Dissertation on deterministic latency guarantees in multi-tenant cloud fabrics.

  ],
  [
    Berlin, Germany

    Okt 2001 – Jul 2004

  ],
  degree-column: [
    #strong[Doctor of Science]
  ],
)

#education-entry(
  [
    #strong[Technical University of Berlin 2], Computer Science & Parallel Architectures

    - GPA \/ Honors: Summa Cum Laude

    - Dissertation on deterministic latency guarantees in multi-tenant cloud fabrics.

  ],
  [
    Berlin, Germany

    Okt 2002 – Jul 2005

  ],
  degree-column: [
    #strong[Master of Science]
  ],
)

== Kenntnisse & Fähigkeiten

#strong[Core Architecture:] Distributed Systems, C++20, Rust

#strong[Infrastructure:] Kubernetes

#strong[High Performance Computing:] MPI \/ OpenMP, RDMA InfiniBand

== Projekte

#regular-entry(
  [
    #strong[#link("https://github.com/hpc/orchestrator")[HPC-Orchestrator-1]]

    #summary[Rust, Tokio, gRPC, eBPF]

    - Kernel-bypass networking scheduler for heterogeneous accelerator nodes.

  ],
  [
    Jan 2021 – Jan 2023

  ],
)

#regular-entry(
  [
    #strong[#link("https://github.com/hpc/orchestrator")[HPC-Orchestrator-2]]

    #summary[Rust, Tokio, gRPC, eBPF]

    - Kernel-bypass networking scheduler for heterogeneous accelerator nodes.

  ],
  [
    Jan 2021 – Jan 2023

  ],
)

#regular-entry(
  [
    #strong[#link("https://github.com/hpc/orchestrator")[HPC-Orchestrator-3]]

    #summary[Rust, Tokio, gRPC, eBPF]

    - Kernel-bypass networking scheduler for heterogeneous accelerator nodes.

  ],
  [
    Jan 2021 – Jan 2023

  ],
)

== Sprachen

#strong[Sprachen:] Deutsch (Muttersprache), English (Fließend), Français (Gute Kenntnisse)
