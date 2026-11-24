import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { LoginPage, loginDestination } from "../pages/LoginPage";
import "../i18n/config";

test("renders login page", () => {
  const { container } = render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
  expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  const animatedBackground = container.querySelector(
    '[data-login-background="grid-drift ambient-glow"]',
  );
  expect(animatedBackground).toBeInTheDocument();
  const orbitWrapper = container.querySelector('[data-login-orbits="true"]');
  expect(orbitWrapper).toBeInTheDocument();
  expect(orbitWrapper).toHaveStyle({ zIndex: "1" });
  expect(
    orbitWrapper?.querySelectorAll(":scope > [data-orbit-ring]") ?? [],
  ).toHaveLength(2);
});

test("manual logout sends the next account to its own default page", () => {
  expect(
    loginDestination(
      { require_password_change: false, default_page: "dashboard" },
      { manualLogout: true, from: { pathname: "/tickets/42" } },
      "/clients/7/profile",
    ),
  ).toBe("/dashboard");
});

test("client portal login never restores an employee page", () => {
  expect(
    loginDestination(
      {
        require_password_change: false,
        default_page: "dashboard",
        user_type: "CLIENT_PORTAL",
      },
      { from: { pathname: "/system", search: "?tab=general" } },
      "/tickets/42",
    ),
  ).toBe("/portal");
});
