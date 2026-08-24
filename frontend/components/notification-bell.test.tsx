import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Notification } from "@/lib/storefront";

const useNotificationsMock = vi.fn();

vi.mock("@/components/notification-provider", () => ({
  useNotifications: () => useNotificationsMock(),
}));

const { default: NotificationBell } = await import("./notification-bell");

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n1",
    user_id: "u1",
    type: "order_confirmed",
    message: "Your order has been confirmed.",
    read_status: false,
    timestamp: "2026-08-24T10:00:00Z",
    ...overrides,
  };
}

describe("NotificationBell", () => {
  const markAllAsRead = vi.fn();
  const markAsRead = vi.fn();

  beforeEach(() => {
    markAllAsRead.mockReset();
    markAsRead.mockReset();
  });

  it("shows the unread count in the badge", () => {
    useNotificationsMock.mockReturnValue({
      notifications: [
        makeNotification({ id: "n1", read_status: false }),
        makeNotification({ id: "n2", read_status: false }),
        makeNotification({ id: "n3", read_status: true }),
      ],
      unreadCount: 2,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("does not mark everything read just from opening the dropdown", async () => {
    useNotificationsMock.mockReturnValue({
      notifications: [makeNotification({ read_status: false })],
      unreadCount: 1,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    await userEvent.click(screen.getByLabelText("Open notifications"));

    expect(screen.getByText("Your order has been confirmed.")).toBeInTheDocument();
    expect(markAllAsRead).not.toHaveBeenCalled();
  });

  it("calls markAllAsRead only when the 'Mark all read' button is clicked", async () => {
    useNotificationsMock.mockReturnValue({
      notifications: [makeNotification({ read_status: false })],
      unreadCount: 1,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    await userEvent.click(screen.getByLabelText("Open notifications"));
    await userEvent.click(screen.getByText("Mark all read"));

    expect(markAllAsRead).toHaveBeenCalledTimes(1);
  });

  it("marks a single unread notification as read when clicked", async () => {
    useNotificationsMock.mockReturnValue({
      notifications: [
        makeNotification({ id: "n1", message: "First", read_status: false }),
      ],
      unreadCount: 1,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    await userEvent.click(screen.getByLabelText("Open notifications"));
    fireEvent.click(screen.getByText("First"));

    expect(markAsRead).toHaveBeenCalledWith("n1");
    expect(markAllAsRead).not.toHaveBeenCalled();
  });

  it("does not call markAsRead again for an already-read notification", async () => {
    useNotificationsMock.mockReturnValue({
      notifications: [
        makeNotification({ id: "n1", message: "Already read", read_status: true }),
      ],
      unreadCount: 0,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    await userEvent.click(screen.getByLabelText("Open notifications"));
    fireEvent.click(screen.getByText("Already read"));

    expect(markAsRead).not.toHaveBeenCalled();
  });

  it("shows an empty state when there are no notifications", async () => {
    useNotificationsMock.mockReturnValue({
      notifications: [],
      unreadCount: 0,
      markAllAsRead,
      markAsRead,
    });

    render(<NotificationBell />);

    await userEvent.click(screen.getByLabelText("Open notifications"));

    expect(screen.getByText("You have no notifications yet.")).toBeInTheDocument();
  });
});
