import { useId } from "react";
import type { CourseSummary } from "../api/types";

export const ALL_COURSES = "all";

interface Props {
  courses: CourseSummary[];
  value: string;
  onChange: (value: string) => void;
}

export function CourseSelect({ courses, value, onChange }: Props) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>Course</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value={ALL_COURSES}>All courses</option>
        {courses.map((course) => (
          <option key={course.course_code} value={course.course_code}>
            {course.course_code} – {course.course_name}
          </option>
        ))}
      </select>
    </div>
  );
}
