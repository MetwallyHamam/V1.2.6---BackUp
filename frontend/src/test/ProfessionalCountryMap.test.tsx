import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfessionalCountryMap } from "../components/ProfessionalCountryMap";

describe("ProfessionalCountryMap", () => {
  it("renders country geometry immediately and opens a highlighted market", () => {
    const onOpen = vi.fn();
    const { container } = render(
      <ProfessionalCountryMap rows={[{ key: "eg", label: "Egypt", value: 12 }]} onOpen={onOpen} />,
    );

    expect(container.querySelectorAll("svg path").length).toBeGreaterThan(100);
    const egypt = screen.getByLabelText("Egypt: 12");
    expect(egypt).toHaveAttribute("fill", "#4f46e5");
    fireEvent.click(egypt);
    expect(onOpen).toHaveBeenCalledWith({ key: "eg", label: "Egypt", value: 12 });
  });
});
