"use client";

import {BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer} from "recharts";

export default function CustomChart({ data }) {

    const chartData =
        data.labels.map((label, i) => ({
            name: label,
        value: data.values[i]
        }));

    return (
        <div className="w-full h-72 bg-white rounded-2xl p-4 border border-gray-200 my-4">
            <ResponsiveContainer>
                <BarChart data={chartData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar
                        dataKey="value"
                        radius={[8,8,0,0]}
                    />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}