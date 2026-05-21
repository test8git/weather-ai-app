"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function TemperatureChart({ forecast }) {

  // Prepare chart data
  const chartData = forecast.map((item) => {

    const date = new Date(item.date);

    return {
      time: date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
      temp: item.temp,
    };
  });

  return (
    <div className="bg-white rounded-3xl shadow p-5 mt-6">

      <h2 className="text-2xl font-bold mb-5">
        24-Hour Temperature
      </h2>

      <div className="w-full h-[300px]">

        <ResponsiveContainer width="100%" height="100%">

          <LineChart data={chartData}>

            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="time" />

            <YAxis />

            <Tooltip />

            <Line
              type="monotone"
              dataKey="temp"
              strokeWidth={3}
            />

          </LineChart>

        </ResponsiveContainer>

      </div>

    </div>
  );
}