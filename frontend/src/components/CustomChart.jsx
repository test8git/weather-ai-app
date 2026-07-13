import {
    ResponsiveContainer,
    LineChart,
    Line,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    AreaChart,
    Area,
    RadarChart,
    Radar,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ScatterChart,
    Scatter,
    ComposedChart,
    CartesianGrid,
    Tooltip,
    Legend,
    XAxis,
    YAxis
} from "recharts";

export default function CustomChart({ data })
{
    if (!data)
        return null;

    const colors = [
        "#3b82f6",
        "#22c55e",
        "#ef4444",
        "#f59e0b",
        "#8b5cf6",
        "#06b6d4"
    ];

    switch (data.type)
    {
        case "line":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={data.data}>
                        <CartesianGrid strokeDasharray="3 3"/>
                        <XAxis dataKey={data.xKey}/>
                        <YAxis/>
                        <Tooltip/>
                        <Legend/>

                        {data.series.map((s,index)=>

                            <Line
                                key={index}
                                dataKey={s.dataKey}
                                name={s.name}
                                stroke={colors[index%colors.length]}
                            />

                        )}

                    </LineChart>
                </ResponsiveContainer>
            );

        case "bar":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={data.data}>
                        <CartesianGrid strokeDasharray="3 3"/>
                        <XAxis dataKey={data.xKey}/>
                        <YAxis/>
                        <Tooltip/>
                        <Legend/>

                        {data.series.map((s,index)=>

                            <Bar
                                key={index}
                                dataKey={s.dataKey}
                                fill={colors[index%colors.length]}
                            />

                        )}

                    </BarChart>
                </ResponsiveContainer>
            );

        case "area":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <AreaChart data={data.data}>
                        <CartesianGrid strokeDasharray="3 3"/>
                        <XAxis dataKey={data.xKey}/>
                        <YAxis/>
                        <Tooltip/>
                        <Legend/>

                        {data.series.map((s,index)=>

                            <Area
                                key={index}
                                dataKey={s.dataKey}
                                fill={colors[index%colors.length]}
                                stroke={colors[index%colors.length]}
                            />

                        )}

                    </AreaChart>
                </ResponsiveContainer>
            );

        case "pie":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <PieChart>

                        <Pie
                            data={data.data}
                            dataKey={data.valueKey}
                            nameKey={data.nameKey}
                            outerRadius={150}
                            label
                        >

                            {data.data.map((entry,index)=>

                                <Cell
                                    key={index}
                                    fill={colors[index%colors.length]}
                                />

                            )}

                        </Pie>

                        <Tooltip/>
                        <Legend/>

                    </PieChart>
                </ResponsiveContainer>
            );

        case "scatter":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <ScatterChart>

                        <CartesianGrid/>

                        <XAxis
                            type="number"
                            dataKey={data.xKey}
                        />

                        <YAxis
                            type="number"
                            dataKey={data.yKey}
                        />

                        <Tooltip/>

                        <Scatter
                            data={data.data}
                            fill="#3b82f6"
                        />

                    </ScatterChart>
                </ResponsiveContainer>
            );

        case "radar":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <RadarChart data={data.data}>

                        <PolarGrid/>

                        <PolarAngleAxis dataKey={data.xKey}/>

                        <PolarRadiusAxis/>

                        <Legend/>

                        {data.series.map((s,index)=>

                            <Radar
                                key={index}
                                dataKey={s.dataKey}
                                stroke={colors[index]}
                                fill={colors[index]}
                                fillOpacity={0.5}
                            />

                        )}

                    </RadarChart>
                </ResponsiveContainer>
            );

        case "composed":

            return (
                <ResponsiveContainer width="100%" height={400}>
                    <ComposedChart data={data.data}>

                        <CartesianGrid/>

                        <XAxis dataKey={data.xKey}/>

                        <YAxis/>

                        <Tooltip/>

                        <Legend/>

                        {data.series.map((s,index)=>

                            index===0 ?

                                <Bar
                                    key={index}
                                    dataKey={s.dataKey}
                                    fill={colors[index]}
                                />

                            :

                                <Line
                                    key={index}
                                    dataKey={s.dataKey}
                                    stroke={colors[index]}
                                />

                        )}

                    </ComposedChart>
                </ResponsiveContainer>
            );

        default:
            return <div>Unsupported chart type</div>;
    }
}