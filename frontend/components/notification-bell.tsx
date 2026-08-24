"use client";

import { useState } from "react";

import { useNotifications } from "@/components/notification-provider";

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    markAllAsRead,
    markAsRead,
  } = useNotifications();

  const handleOpen = () => {
    setIsOpen((current) => !current);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleOpen}
        className="relative inline-flex items-center gap-2 text-sm font-medium text-slate-700 transition hover:text-slate-950"
        aria-label="Open notifications"
      >
        <span
  aria-hidden="true"
  className="text-lg leading-none"
>
  🔔
</span>

        <span
          className={`inline-flex min-w-6 items-center justify-center rounded-full px-2 py-0.5 text-xs font-bold ${
            unreadCount > 0
              ? "bg-rose-500 text-white"
              : "bg-slate-200 text-slate-600"
          }`}
        >
          {unreadCount}
        </span>
      </button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-3 w-80 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h3 className="font-semibold text-slate-900">
              Notifications
            </h3>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => void markAllAsRead()}
                className="text-xs font-semibold text-cyan-700 hover:text-cyan-900"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-slate-500">
                You have no notifications yet.
              </p>
            ) : (
              notifications.map((notification) => (
                <article
                  key={notification.id}
                  role={notification.read_status ? undefined : "button"}
                  tabIndex={notification.read_status ? undefined : 0}
                  onClick={() =>
                    !notification.read_status &&
                    void markAsRead(notification.id)
                  }
                  onKeyDown={(event) => {
                    if (
                      !notification.read_status &&
                      (event.key === "Enter" || event.key === " ")
                    ) {
                      event.preventDefault();
                      void markAsRead(notification.id);
                    }
                  }}
                  className={`border-b border-slate-100 px-4 py-3 last:border-b-0 ${
                    notification.read_status
                      ? "bg-white"
                      : "cursor-pointer bg-cyan-50 hover:bg-cyan-100"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-slate-800">
                      {notification.message}
                    </p>

                    {!notification.read_status && (
                      <span
                        aria-hidden="true"
                        className="mt-1 inline-block h-2 w-2 flex-none rounded-full bg-cyan-500"
                      />
                    )}
                  </div>

                  <p className="mt-1 text-xs text-slate-500">
                    {new Date(
                      notification.timestamp
                    ).toLocaleString()}
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}