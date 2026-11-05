// content.js — all the writing in the playground lives here, so it can be
// edited without touching any code. Plain text, plus <b>, <i> and <code>.
//
// Per module:
//   purpose   the everyday problem the module answers
//   approach  the decisions behind it, and why
//   result    how to read what comes out
//   source    where the formulas come from

export const NOTES = {
  beams: {
    purpose: "Shelves, brackets, bridges, robot arms: anything that spans a gap and carries weight is a beam. Before building one you want to know two things. Will it break, and will it sag too much?",
    approach: [
      "Closed-form Euler-Bernoulli equations instead of a finite element model. They're exact for slender beams, they run instantly, and every number traces back to one textbook equation you can check by hand.",
      "Strength and stiffness are reported separately, because a beam can be strong enough and still sag too much to use. The reading compares the sag with the common span/360 limit.",
      "Sections and materials are inputs rather than hard-coded, so the same function covers a steel bar, an aluminium tube or a nylon rod.",
    ],
    result: "Stress is compared against the material's yield strength to give the safety factor. Deflection is the sag at the worst point. The shear and moment diagrams show where along the beam the load is felt most.",
    source: "Hibbeler, Mechanics of Materials: beam deflection tables",
  },
  stress: {
    purpose: "Real parts are rarely loaded one way at a time. A shaft can be bent and twisted together. This module combines everything acting at one point and answers one question: will the material yield there?",
    approach: [
      "Principal stresses come from the Mohr's circle relations, so the diagram you see is the same math the code runs.",
      "Von Mises is the pass/fail check because it predicts yielding in ductile metals best. Tresca is shown alongside as the more conservative check.",
      "The principal angle is solved with atan2, not atan, so it stays correct in every quadrant and when σx equals σy.",
    ],
    result: "σ₁ and σ₂ are the largest pull and push at that point. Von Mises turns the whole stress state into one number to compare with the yield strength.",
    source: "Hibbeler; Beer & Johnston, Mechanics of Materials: plane stress",
  },
  gears: {
    purpose: "Motors spin fast with little torque, and most machines want the opposite. A gear train trades one for the other. This module follows the speed and torque through every shaft.",
    approach: [
      "The train is modelled stage by stage, with each driven gear sharing a shaft with the next driver, the same way a real reducer is built.",
      "Efficiency compounds per mesh rather than being applied once, because losses stack up in multi-stage gearboxes.",
      "Centre distance comes out of the gear module, so the result is a layout you could actually machine.",
    ],
    result: "The overall ratio is the product of the stage ratios. Output speed is divided by it, and output torque is multiplied by it, minus the losses.",
    source: "Standard spur-gear relations (Shigley's Mechanical Engineering Design)",
  },
  thermal: {
    purpose: "Heat makes parts grow. Rails buckle, bolts loosen, and buildings lose energy through their walls. This module covers both sides: how parts move with temperature, and how heat moves through them.",
    approach: [
      "Free expansion and clamped stress are shown side by side, because the same temperature change is harmless or dangerous depending only on whether the part can move.",
      "The clamped stress (E·α·ΔT) doesn't depend on length, which surprises most people, so the chart plots it against ΔT alone.",
      "Heat loss treats the wall and the outside air film as resistances in series, the standard way to stack layers.",
    ],
    result: "ΔL is how far a free bar grows. The clamped stress is what it pushes with if it can't grow. For walls, q is the heat lost per second, in watts.",
    source: "Hibbeler, Mechanics of Materials · Fourier's law and Newton's law of cooling",
  },
  bearings: {
    purpose: "Every rotating machine rides on bearings, and they wear out. This module predicts how long one will last, and which one to order when it won't last long enough.",
    approach: [
      "Uses the ISO 281 basic rating life, the same method bearing catalogues are built on, with exponent 3 for ball bearings and 10/3 for rollers.",
      "Solves the problem in both directions, life from rating and rating from life, because in practice you start from the life you need and go shopping.",
      "Plotted on log scales so the power law shows as a straight line.",
    ],
    result: "L10 is the life that 90% of identical bearings will reach. The required rating is the minimum C to look for in a catalogue.",
    source: "ISO 281 basic rating life",
  },
  buckling: {
    purpose: "A long, thin column can fail far below its material strength by suddenly bowing sideways. Think of a ruler pushed from both ends. This module finds the load where that happens.",
    approach: [
      "Picks between the Euler and Johnson formulas automatically at the transition slenderness, since Euler alone overestimates the strength of short columns.",
      "Uses the weak-axis moment of inertia, because a column always buckles about its weakest direction.",
      "End conditions map to the effective length factor K, so the same function covers a flagpole, a pinned strut or a fixed post.",
    ],
    result: "The critical load is where the column fails. The chart shows which regime it sits in and how close the applied load gets.",
    source: "Shigley's Mechanical Engineering Design, Ch. 4 (Columns)",
  },
  materials: {
    purpose: "Every calculation needs material properties. Instead of retyping them each time, the toolkit keeps one database that every module reads from.",
    approach: [
      "Each material is defined once, in SI units, and looked up by name everywhere else, so a correction fixes every module at the same time.",
      "The chart uses log scales in the style of an Ashby chart, so plastics and titanium fit on the same axes.",
      "Strength and stiffness per kilogram are included, because for anything that moves or flies those matter more than raw strength.",
    ],
    result: "Points further up and to the left are strong for their weight. Pick a material here, then use it in any other module.",
    source: "Typical handbook values (MatWeb, ASM). Confirm against a data sheet for real designs.",
  },
  units: {
    purpose: "Datasheets come in psi, drawings in mm and suppliers in lbf. Mixing them up is one of the easiest ways to get an answer that's off by a factor of a thousand.",
    approach: [
      "Each unit stores one number, its size in SI, and every conversion goes through SI. That means n entries instead of n² conversion pairs.",
      "Temperature gets its own path through Celsius, since its scales have offsets, not just multipliers.",
      "Unknown units raise a clear error listing the options, instead of failing silently.",
    ],
    result: "The table converts the value into every unit in the category at once. Click a row to make it the target.",
    source: "Exact SI definitions (1 in = 25.4 mm, 1 lbf = 4.448 N …)",
  },
};

// The About page. Edit freely: the layout adapts to however many sections
// and items you add.
export const ABOUT = {
  title: "Why I built Mech Lab",
  lede: "As a mechanical engineering student at the University of Waterloo, I kept solving the same hand calculations over and over: beam deflections, gear ratios, bearing life. Mech Lab is those calculations written once, tested properly, and made fast enough to explore.",
  sections: [
    {
      heading: "The problem",
      body: "Hand calculations are slow and easy to get wrong, and a spreadsheet hides its formulas in cells. I wanted something in between: real code, readable formulas, and answers I could trust because every one is checked against a worked example.",
    },
    {
      heading: "Decisions",
      items: [
        ["Closed-form equations, not FEA", "Exact for the standard cases, instant to run, and every result traces back to one textbook equation."],
        ["One shared materials database", "Every module looks up properties by name, so a material is defined once and fixed once."],
        ["Tested against hand calculations", "Each formula's test compares with a value worked out by hand, not just a check that the code runs."],
        ["Pure Python core", "No heavy dependencies for the maths, which is what lets this page run the real package in your browser."],
      ],
    },
    {
      heading: "How this page works",
      body: "The calculator panels run the actual mech_toolkit Python package, unchanged, inside your browser through Pyodide (CPython compiled to WebAssembly). Nothing is sent to a server. Each panel also shows the exact Python call, so any result can be reproduced from a terminal.",
    },
    {
      heading: "Verification",
      items: [
        ["Automated tests", "pytest suite, run by GitHub Actions on Python 3.9 to 3.12 for every change."],
        ["Reference values", "Formulas checked against standard texts (Hibbeler, Beer & Johnston, Shigley) and ISO 281."],
        ["Same code everywhere", "The site deploys straight from the repository, so the page always matches the package."],
      ],
    },
  ],
  links: [
    ["Source code", "https://github.com/Haneet10/Mech-Lab"],
    ["Formula reference", "https://github.com/Haneet10/Mech-Lab/blob/main/docs/theory.md"],
    ["Truss Lab", "https://haneet10.github.io/Truss-Lab/"],
  ],
};
