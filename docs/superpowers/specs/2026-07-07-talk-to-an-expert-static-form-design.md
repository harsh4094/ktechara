# Talk to an Expert — Static Form Rebuild

## Problem

`talk-to-an-expert.html` currently renders its form via a HubSpot embed:

```html
<script src="https://js-eu1.hsforms.net/forms/embed/v2.js"></script>
<script>
  hbspt.forms.create({ portalId: "3017156", formId: "4ab67848-62f3-41cd-a09d-7a201c55f1d5", region: "eu1" });
</script>
```

None of the form's fields, options, labels, or styling exist in the static HTML — HubSpot's script injects all of it at runtime. We don't have access to modify or reconfigure that HubSpot form, and the site has no active backend to submit to. We need the form's markup rebuilt as plain static HTML that visually and structurally matches the live rendered version (per user-provided screenshots), with a front-end-only submit placeholder until a real submission endpoint is decided later.

## Scope

- File: `talk-to-an-expert.html` only.
- No changes to `contact-us/index.html` or the ~157 other pages embedding HubSpot forms/CTAs elsewhere in the site — out of scope for this task.
- No changes to `_header.html` / `_footer.html`.

## Reference Material

Two user screenshots of the live rendered form supplied the exact field set, layout, and three dropdowns' option lists:

- **Job Function\*** (`<select>`): Please Select, Customer Success / Service Delivery, Finance, Human Resources / Internal Communications, Legal and Compliance, Marketing, Operations, Procurement / Purchasing, Product Management, Project and Programme Management, Quality Assurance, Research and Development, "Sales: Pre-Sales / Business Development / Account Management", Strategy and Leadership, Technical / IT
- **Seniority\*** (`<select>`): Please Select, C Level, Senior, Mid Level, Junior
- **Number of Employees\*** (`<select>`): Please Select, Under 10, Below 150, Between 150 and 1500, Between 1500-5000, Above 5000

## Form Structure (top to bottom)

1. First Name* / Last Name* — text inputs, 2-column row
2. Job Function* / Seniority* — `<select>`s, 2-column row
3. Business Email* / Company Name* — text inputs (email uses `type="email"`), 2-column row
4. Product/Service* — checkbox group, full width, 13 items exactly as listed in the screenshot (Fresh Intranet; Automation, Data & AI Consulting (...); Cyber Consulting (...); Managed Cyber Services (...); Managed IT Services and Support; Software & Licensing (...); Technology Sourcing and Management (...); D365 and Business Applications Consulting; Digital Employee Experience (...); Hybrid Cloud Consulting; Sovereign Cloud / Infrastructure as a Service; Unified Communications; Other (please expand in "how can we help")) — real `<input type="checkbox">` elements, not radios
5. Number of Employees* — `<select>`, full width
6. How can we help?* / How did you hear about us?* — two `<textarea>`s, 2-column row
7. Consent copy (static paragraph, reuse existing "Manage Preferences" / `hello@advania.co.uk` text) + "I agree to receive marketing updates about Advania from the Advania UK group." checkbox (not required)
8. Terms of Use / Privacy Policy paragraph (static text, reuse existing links) + consent-on-submit sentence
9. Submit button: "Connect now" — pink pill button matching site's existing primary-button styling (hover: transparent bg / pink text / pink border, matching the pattern already defined for `.custom-hubspot-form input.hs-button.primary.large`)

reCAPTCHA badge is dropped entirely — it was HubSpot's injected badge and has no function without their backend verifying tokens.

## Validation & Submit Behavior

- All fields marked `*` in the screenshot are `required` (native HTML5 validation), except the marketing-consent checkbox.
- Product/Service checkbox group needs "at least one checked" enforced via a small inline JS validator (no native HTML5 support for "at least one of N checkboxes").
- On valid submit: `preventDefault()`, hide the form, reveal a "Thank you" confirmation message in its place. No data is transmitted anywhere — this is a front-end-only placeholder.
- Add an HTML comment near the form noting the submit handler is a placeholder pending a real submission endpoint, so a future maintainer doesn't mistake it for a working integration.

## Styling Approach

- The outer Elementor wrapper divs (`elementor-element-b8ec6e0`, `2b0439c`, `c0a4a6a`) already provide the card background (`#F6F7F8`), box-shadow, and padding via existing per-page CSS (`post-32750.css`) — these are untouched.
- New scoped CSS (added inline in `talk-to-an-expert.html`, scoped under a new class e.g. `.static-expert-form`) reproduces: 2-column responsive grid (collapsing to 1 column on narrow viewports, consistent with the rest of the site's breakpoints), input/select/textarea borders and spacing matching the screenshot, checkbox list spacing, and the pink pill submit button with hover state.
- Reuses existing site color tokens/fonts where available rather than introducing new hard-coded values, checking `global-styles-inline-css` custom properties first.

## Out of Scope / Follow-ups

- Wiring real submission (e.g., HubSpot Forms Submission API, mailto, or another backend) is a separate future task once an endpoint is decided.
- Rolling this same static-form pattern out to `contact-us/index.html` or blog-page HubSpot CTAs is not part of this task.
