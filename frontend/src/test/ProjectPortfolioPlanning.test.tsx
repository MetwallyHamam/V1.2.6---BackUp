import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { ProjectPortfolioPlanning } from "../components/ProjectPortfolioPlanning";

const today = new Date();
const date = new Date(today.getFullYear(), today.getMonth(), 12).toLocaleDateString("sv-SE");
const projects = [
  { id: 4, name: "Clinic rollout", project_number: "001", planned_start_date: date, planned_end_date: date },
  { id: 5, name: "Finance rollout", project_number: "002", planned_start_date: date, planned_end_date: date },
];

it("links planned starts and due dates to the schedule and navigates between months", () => {
  render(<MemoryRouter><ProjectPortfolioPlanning view="calendar" projects={projects} /></MemoryRouter>);
  expect(screen.getByRole("link", { name: /Start · 001 Clinic rollout/ })).toHaveAttribute("href", "/projects/4/schedule");
  expect(screen.getByRole("link", { name: /Due · 001 Clinic rollout/ })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Next month" }));
  expect(screen.queryByRole("link", { name: /Clinic rollout/ })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Today" }));
  expect(screen.getByRole("link", { name: /Due · 001 Clinic rollout/ })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Gantt" }));
  expect(screen.getByRole("link", { name: /Clinic rollout,/ })).toHaveAttribute("href", "/projects/4/schedule");
  fireEvent.click(screen.getByRole("button", { name: "Month" }));
  expect(screen.getByRole("link", { name: /Due · 001 Clinic rollout/ })).toBeVisible();
});

it("filters timeline windows by product and links each window to its project", () => {
  render(<MemoryRouter><ProjectPortfolioPlanning view="timeline" projects={projects} products={[
    { project_id: 4, product_id: 10, name: "Clinic" },
    { project_id: 5, product_id: 11, name: "Finance" },
  ]} /></MemoryRouter>);
  expect(screen.getByRole("link", { name: /Clinic rollout,/ })).toHaveAttribute("href", "/projects/4/schedule");
  fireEvent.mouseDown(screen.getByRole("combobox", { name: "Product" }));
  fireEvent.click(screen.getByRole("option", { name: "Finance" }));
  expect(screen.queryByRole("link", { name: /Clinic rollout/ })).toBeNull();
  expect(screen.getByRole("link", { name: /Finance rollout,/ })).toHaveAttribute("href", "/projects/5/schedule");
});
