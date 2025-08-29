import { Breadcrumbs, Link, Typography } from "@mui/material";
import { useNavigate, useSearchParams } from "react-router-dom";

import NavigateNextIcon from "@mui/icons-material/NavigateNext";
import React from "react";

const BreadcrumbsNav = ({ items = [] }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  return (
    <Breadcrumbs
      aria-label="breadcrumb"
      separator={<NavigateNextIcon fontSize="small" />}
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return isLast ? (
          <Typography key={index} color="text.primary">
            {item.label}
          </Typography>
        ) : (
          <Link
            key={index}
            underline="hover"
            color="inherit"
            component="button"
            onClick={() => navigate(`${item.href}/?${searchParams.toString()}`)}
          >
            {item.label}
          </Link>
        );
      })}
    </Breadcrumbs>
  );
};

export default BreadcrumbsNav;
