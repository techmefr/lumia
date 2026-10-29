import { render } from "@testing-library/svelte";
import { Cancel01Icon } from "@hugeicons/core-free-icons";
import { describe, expect, it } from "vitest";
import Icon from "./icon.svelte";

type Props = Parameters<typeof Icon>[1];

function icon(props: Partial<Props> = {}) {
  const { container } = render(Icon, { icon: Cancel01Icon, ...props } as Props);
  return container.querySelector("svg")!;
}

describe("a decorative icon", () => {
  it("is hidden from assistive technology", () => {
    const svg = icon();

    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("focusable")).toBe("false");
    expect(svg.hasAttribute("role")).toBe(false);
    expect(svg.hasAttribute("aria-label")).toBe(false);
  });
});

describe("an icon that carries meaning", () => {
  it("is exposed as an image with its label", () => {
    const svg = icon({ label: "Close" });

    expect(svg.getAttribute("role")).toBe("img");
    expect(svg.getAttribute("aria-label")).toBe("Close");
    expect(svg.hasAttribute("aria-hidden")).toBe(false);
  });
});

describe("the rendering", () => {
  it("draws the paths of the chosen icon", () => {
    expect(icon().querySelectorAll("path").length).toBe(Cancel01Icon.length);
  });

  it("passes the class and the size through", () => {
    const svg = icon({ class: "size-4", size: 16 });

    expect(svg.getAttribute("class")).toBe("size-4");
    expect(svg.getAttribute("width")).toBe("16");
  });

  it("applies the stroke width to every path", () => {
    const svg = icon({ strokeWidth: 2 });

    for (const path of svg.querySelectorAll("path"))
      expect(path.getAttribute("stroke-width")).toBe("2");
  });
});
