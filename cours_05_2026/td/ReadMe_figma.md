Objectif de comparer 


```text
I want to build a small product landing page in React and Tailwind.

Use the screenshot files/figma_examples/figma-mcp-demo-clean-product-card.png as visual reference.
Create a clean responsive page with:
- a centered product card matching the screenshot
- a simple hero section above it
- a background similar to the screenshot
- a reusable ProductCard component

Try to match spacing, typography, colors, border radius, shadows and visual hierarchy.

And please write the small product landing page in the folder data/figma_no_mcp/
```

Et ensuite on peut verifier dans le dossier `data/figma_no_mcp/`
```bash
npm run dev
```

Et maintenant on a un lien url pour le svg figma a 
```url
https://www.figma.com/design/t8UYkztzSVUfPAZEE7SvcN/example-pour-mcp-test?node-id=2-2&t=nUcECgjwjWLhtOuz-1
```
On ajoute la connection MCP a figma
```
\add-plugin figma
```

Et on veut tester avec l'aide du MCP Figma
```text
Use the selected Figma frame as the source of truth. The url link is as follows :
https://www.figma.com/design/t8UYkztzSVUfPAZEE7SvcN/example-pour-mcp-test?node-id=2-2&t=nUcECgjwjWLhtOuz-1

Build a small product landing page in React and Tailwind based on this design.

Requirements:
- Create a reusable ProductCard component.
- Create a ProductLandingPage component.
- Respect the Figma layout, spacing, typography hierarchy, colors, border radii and component structure.
- Extract obvious design tokens into constants or Tailwind classes.
- Make the page responsive.
- Keep the implementation clean and easy to modify.

Before coding, inspect the Figma frame and summarize the visual structure you found.

And please write the small product landing page in the folder data/figma_with_mcp/
```