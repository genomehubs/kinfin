import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import BreadcrumbsNav from "../BreadcrumbsNav";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import React from "react";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { setSelectedClusterSet } from "../../app/store/config/slices/uiStateSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";

const Navbar = ({
  onMenuClick,
  breadcrumbs = [],
  variant = "analysis", // "landing" or "analysis"
}) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const handleNewAnalysis = () => {
    navigate("/define-node-labels");
    dispatch(setSelectedClusterSet(null));
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="fixed" color="inherit" sx={{ zIndex: 2002 }}>
        <Toolbar>
          {variant === "analysis" && (
            <IconButton
              size="large"
              edge="start"
              color="inherit"
              aria-label="menu"
              sx={{ mr: 2 }}
              onClick={onMenuClick}
            >
              <MenuIcon />
            </IconButton>
          )}

          <Typography
            variant="h6"
            component="div"
            color="primary"
            onClick={() => navigate("/")}
            sx={{
              flexGrow: 1,
              fontWeight: "bold",
              cursor: "pointer",
              outline: "none",
            }}
            tabIndex={0} // keyboard focusable
            role="button"
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                navigate("/");
              }
            }}
          >
            KinFin
          </Typography>

          {variant === "landing" && (
            <Button
              onClick={handleNewAnalysis}
              color="primary"
              variant="contained"
              sx={{ padding: "6px 16px" }}
            >
              Start Analysis
            </Button>
          )}

          {variant === "analysis" && (
            <Button
              onClick={handleNewAnalysis}
              color="primary"
              variant="contained"
            >
              New Analysis
            </Button>
          )}
        </Toolbar>

        {variant === "analysis" && breadcrumbs.length > 0 && (
          <Toolbar
            variant="dense"
            sx={{ borderTop: "1px solid #ddd", minHeight: "40px" }}
          >
            <BreadcrumbsNav items={breadcrumbs} />
          </Toolbar>
        )}
      </AppBar>
    </Box>
  );
};

export default Navbar;
